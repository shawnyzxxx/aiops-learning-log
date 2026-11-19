# run_eval.py —— 跑评测，输出 recall + 待人工打分的答案
import json
import os
import sys

from rag import retrieve, answer, col

EVAL_FILE = "eval_set.json"
OUT_FILE = "eval_result.json"


def main():
    data = json.load(open(EVAL_FILE, encoding="utf-8"))
    items = data["items"]

    results = []
    hit = 0
    total_answerable = 0
    reject_ok = 0
    total_unanswerable = 0

    for it in items:
        q = it["question"]
        hits = retrieve(q, k=5)
        sources = [m["source"] for _, m, _ in hits]

        rec = {"id": it["id"], "question": q, "answerable": it["answerable"],
               "expected": it.get("expected_source"), "retrieved": sources}

        if it["answerable"]:
            total_answerable += 1
            if it.get("expected_source") in sources:
                hit += 1
                rec["recall_hit"] = True
            else:
                rec["recall_hit"] = False
        else:
            total_unanswerable += 1

        # 生成答案（后面人工打分）
        try:
            r = answer(q, k=5)
            rec["answer"] = r.get("answer", "")
            rec["citations"] = r.get("citations", [])
            rec["confidence"] = r.get("confidence", 0)
            rec["ok"] = r.get("ok", False)
        except Exception as e:
            rec["answer"] = f"[ERROR] {e}"
            rec["ok"] = False

        # 无答案题自动判断是否拒答
        if not it["answerable"]:
            said_unknown = ("没有" in rec["answer"]) or ("未提及" in rec["answer"]) or ("不知道" in rec["answer"])
            rec["reject_ok"] = said_unknown
            if said_unknown:
                reject_ok += 1

        results.append(rec)
        mark = "✓" if rec.get("recall_hit") else ("·" if not it["answerable"] else "✗")
        print(f"[{mark}] {it['id']:>2} {q[:30]}")

    recall = hit / total_answerable if total_answerable else 0
    reject_rate = reject_ok / total_unanswerable if total_unanswerable else 0

    summary = {
        "recall@5": round(recall, 3),
        "reject_rate": round(reject_rate, 3),
        "total": len(items),
        "answerable": total_answerable,
        "unanswerable": total_unanswerable,
    }
    print("\n=== 结果 ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    json.dump({"summary": summary, "items": results}, open(OUT_FILE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n明细已写入 {OUT_FILE}，请人工给 answer 打 0/1/2 分")


if __name__ == "__main__":
    main()
