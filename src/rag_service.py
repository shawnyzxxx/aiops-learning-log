# rag_service.py —— D13：给第 3 周调用的稳定 RAG 接口
"""统一入口只依赖 rag.answer，不暴露 Chroma、BM25 或 prompt 细节。"""

from rag import answer as _answer


def ask(question: str) -> dict:
    """回答运维问题，返回固定结构 {answer, citations, confidence, ok}。

    - 默认使用 D12 的向量 + BM25 混合检索。
    - 异常不向上抛给告警闭环；返回 ok=False 和可读 error。
    - answer/citations/confidence 始终存在，调用方不用判断缺字段。
    """
    if not isinstance(question, str) or not question.strip():
        return {"answer": "", "citations": [], "confidence": 0.0,
                "ok": False, "error": "question must be a non-empty string"}

    try:
        result = _answer(question.strip())
        ok = bool(result.get("ok", False))
        return {
            "answer": result.get("answer", "") if ok else "",
            "citations": list(result.get("citations", [])) if ok else [],
            "confidence": float(result.get("confidence", 0.0)) if ok else 0.0,
            "ok": ok,
            **({} if ok else {"error": result.get("error", "generation failed")}),
        }
    except Exception as exc:
        return {"answer": "", "citations": [], "confidence": 0.0,
                "ok": False, "error": f"{type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    import json
    import sys
    question = " ".join(sys.argv[1:]) or "服务响应突然变慢应该先看什么"
    print(json.dumps(ask(question), ensure_ascii=False, indent=2))
