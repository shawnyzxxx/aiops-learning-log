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

load_dotenv()

client = OpenAI(api_key=os.environ["API_KEY"], base_url=os.environ["BASE_URL"])
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
    vec = client.embeddings.create(model=EMB_MODEL, input=[question]).data[0].embedding
    r = col.query(query_embeddings=[vec], n_results=k)
    return list(zip(r["documents"][0], r["metadatas"][0], r["distances"][0]))


def build_context(hits):
    parts = []
    for doc, meta, _ in hits:
        parts.append(f"【{meta['source']}】\n{doc}")
    return "\n\n---\n\n".join(parts)


def answer(question: str, k: int = 5) -> dict:
    hits = retrieve(question, k)
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
