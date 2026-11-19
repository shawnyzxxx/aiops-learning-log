# rag.py —— 检索 + 生成，输出结构化结果
import os
import json
import sys
from typing import List

# 和 build_index.py 一样：这四行必须在 import chromadb 之前
__import__('pysqlite3')
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

from dotenv import load_dotenv
from openai import OpenAI
import chromadb
from pydantic import BaseModel, ValidationError

from hybrid import build_bm25, bm25_search, merge_hits

load_dotenv()

# timeout 必须显式给：SDK 默认 600 秒，网络一抖就「卡住」几分钟（D12 踩过）
client = OpenAI(api_key=os.environ["API_KEY"], base_url=os.environ["BASE_URL"],
                timeout=30.0, max_retries=2)
CHAT_MODEL = os.environ.get("CHAT_MODEL", "Qwen/Qwen2.5-7B-Instruct")
EMB_MODEL = os.environ.get("EMB_MODEL", "BAAI/bge-m3")   # 默认值必须和建库时同一个
col = chromadb.PersistentClient(path="chroma").get_collection("runbooks")

SYSTEM = """你是一个运维知识库助手。必须遵守：
1. 只能依据【资料】回答，资料里没有就说"资料中没有相关信息"，不要编造
2. 输出必须是 JSON，格式：
   {"answer": "回答内容", "citations": ["文件名1", "文件名2"], "confidence": 0到1的小数}
3. citations 只填资料里出现过的文件名
4. confidence 表示你对答案的把握，资料没覆盖就填 0.2 以下"""


class RagAnswer(BaseModel):
    answer: str
    citations: List[str]
    confidence: float


def retrieve(question: str, k: int = 5):
    """D8/D9 的纯向量检索。D12 起默认走 hybrid_retrieve，这个保留给对比实验。"""
    vec = client.embeddings.create(model=EMB_MODEL, input=[question]).data[0].embedding
    r = col.query(query_embeddings=[vec], n_results=k)
    return list(zip(r["documents"][0], r["metadatas"][0], r["distances"][0]))


_bm25_cache = {}


def hybrid_retrieve(question: str, k_vec: int = 10, k_bm: int = 10, limit: int = 10):
    """D12：向量 + BM25 混合检索。

    k_vec / k_bm：两路各自召回多少条；limit：合并去重后给模型多少条。
    实测（2026-11-19，179 块）：5/5→8 时 recall@5 = 0.867，10/10→10 时 = 0.933。
    注意 recall@5 的「5」是评分口径，limit 是喂给模型的上下文条数，两者独立。
    """
    all_docs = col.get()
    docs, metas = all_docs["documents"], all_docs["metadatas"]

    key = len(docs)
    if key not in _bm25_cache:
        _bm25_cache.clear()                 # 索引重建后旧 BM25 作废
        _bm25_cache[key] = build_bm25(docs)
    bm25 = _bm25_cache[key]

    vec = client.embeddings.create(model=EMB_MODEL, input=[question]).data[0].embedding
    r = col.query(query_embeddings=[vec], n_results=k_vec)
    vec_hits = list(zip(r["documents"][0], r["metadatas"][0], r["distances"][0]))

    bm_hits = bm25_search(bm25, docs, metas, question, k=k_bm)
    return merge_hits(vec_hits, bm_hits, limit=limit)


def build_context(hits):
    parts = []
    for doc, meta, _ in hits:
        parts.append(f"【{meta['source']}】\n{doc}")
    return "\n\n---\n\n".join(parts)


def answer(question: str, k: int = 5, hybrid: bool = True, hits=None) -> dict:
    """hybrid=True 走混合检索（D12 起默认）；hits 可由调用方传入，避免评测时重复检索。"""
    if hits is None:
        hits = hybrid_retrieve(question) if hybrid else retrieve(question, k)
    context = build_context(hits)

    resp = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"【资料】\n{context}\n\n【问题】\n{question}"},
        ],
        response_format={"type": "json_object"},   # 强制 JSON
        temperature=0.1,                            # 越低越稳定
    )
    raw = resp.choices[0].message.content

    try:
        data = json.loads(raw)
        parsed = RagAnswer(**data)
        return {"ok": True, **parsed.model_dump(), "raw": raw}
    except (json.JSONDecodeError, ValidationError) as e:
        return {"ok": False, "error": str(e), "raw": raw}


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "服务响应突然变慢应该先看什么"
    print(json.dumps(answer(q), ensure_ascii=False, indent=2))
