# run_eval.py —— D11-D13 统一评测入口
"""支持独立输入输出和只复测检索，保留严格口径与等价来源口径。"""
import argparse
import json

from rag import hybrid_retrieve, answer

RECALL_K = 5
CONTEXT_K = 10
ANSWER_FIELDS = ("answer", "citations", "confidence", "ok", "score", "note")


def parse_args():
    parser = argparse.ArgumentParser(description="Run RAG retrieval and answer evaluation")
    parser.add_argument("--eval-file", default="eval_set.json")
    parser.add_argument("--output", default="eval_result.json")
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--reuse-answers-from", default=None)
    return parser.parse_args()


def load_previous(path):
    if not path:
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return {x["id"]: x for x in json.load(f).get("items", [])}
    except FileNotFoundError:
        return {}


def main():
    args = parse_args()
    with open(args.eval_file, encoding="utf-8") as f:
        data = json.load(f)
    previous = load_previous(args.reuse_answers_from or args.output)
    results = []
    strict5 = strict10 = equivalent5 = equivalent10 = 0
    reject_ok = total_answerable = total_unanswerable = 0

    for it in data["items"]:
        question = it["question"]
        hits = hybrid_retrieve(question)
        sources5 = [m["source"] for _, m, _ in hits[:RECALL_K]]
        sources10 = [m["source"] for _, m, _ in hits[:CONTEXT_K]]
        expected = it.get("expected_source")
        expected_sources = it.get("expected_sources") or ([expected] if expected else [])
        old = previous.get(it["id"], {})
        rec = {"id": it["id"], "question": question, "answerable": it["answerable"],
               "expected": expected, "expected_sources": expected_sources,
               "retrieved": sources5, "retrieved10": sources10}

        if it["answerable"]:
            total_answerable += 1
            rec["strict_recall_hit"] = expected in sources5
            rec["strict_recall10_hit"] = expected in sources10
            rec["recall_hit"] = any(s in sources5 for s in expected_sources)
            rec["recall10_hit"] = any(s in sources10 for s in expected_sources)
            strict5 += rec["strict_recall_hit"]
            strict10 += rec["strict_recall10_hit"]
            equivalent5 += rec["recall_hit"]
            equivalent10 += rec["recall10_hit"]
        else:
            total_unanswerable += 1

        if args.retrieval_only:
            for field in ANSWER_FIELDS:
                if field in old:
                    rec[field] = old[field]
            rec.setdefault("answer", "")
            rec.setdefault("citations", [])
            rec.setdefault("confidence", 0.0)
            rec.setdefault("ok", False)
        else:
            try:
                generated = answer(question, hits=hits)
                rec["answer"] = generated.get("answer", "")
                rec["citations"] = generated.get("citations", [])
                rec["confidence"] = generated.get("confidence", 0.0)
                rec["ok"] = generated.get("ok", False)
                if "score" in old:
                    rec["score"] = old["score"]
                if "note" in old:
                    rec["note"] = old["note"]
            except Exception as exc:
                rec.update({"answer": f"[ERROR] {type(exc).__name__}: {exc}",
                            "citations": [], "confidence": 0.0, "ok": False})

        if not it["answerable"]:
            text = rec["answer"]
            said_unknown = any(word in text for word in ("没有", "未提及", "不知道"))
            rec["reject_ok"] = said_unknown
            reject_ok += said_unknown

        results.append(rec)
        mark = "✓" if rec.get("recall_hit") else ("·" if not it["answerable"] else "✗")
        print(f"[{mark}] {it['id']:>2} {question[:30]}", flush=True)

    scored = [x["score"] for x in results if x.get("answerable") and isinstance(x.get("score"), (int, float))]
    summary = {
        "eval_version": data.get("eval_version", "d11-single-source-v1"),
        "eval_file": args.eval_file,
        "retrieval_only": args.retrieval_only,
        "recall@5": round(equivalent5 / total_answerable, 3) if total_answerable else 0,
        "recall@10": round(equivalent10 / total_answerable, 3) if total_answerable else 0,
        "strict_recall@5": round(strict5 / total_answerable, 3) if total_answerable else 0,
        "strict_recall@10": round(strict10 / total_answerable, 3) if total_answerable else 0,
        "reject_rate": round(reject_ok / total_unanswerable, 3) if total_unanswerable else 0,
        "total": len(results), "answerable": total_answerable,
        "unanswerable": total_unanswerable,
        "generation_ok": sum(1 for x in results if x.get("ok")),
        "scored_answers": len(scored),
    }
    if scored:
        summary["answer_avg_score"] = round(sum(scored) / len(scored), 3)
        summary["answer_total"] = sum(scored)

    print()
    print("=== 结果 ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "items": results}, f, ensure_ascii=False, indent=2)
    print()
    print(f"明细已写入 {args.output}")


if __name__ == "__main__":
    main()
