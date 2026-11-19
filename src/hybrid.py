# hybrid.py —— D12：向量 + BM25 混合检索（只放工具函数，不自己建 client）
#
# 为什么需要它：纯向量对专有名词（ens33、recall@5、PromQL 运算符）很弱，
# BM25 靠字面重合能补上；但 BM25 不懂同义改写，所以两路各取一部分再合并。
#
# 用法见 rag.hybrid_retrieve()：
#   1) build_bm25(col.get()["documents"])  建一次，缓存起来
#   2) bm25_search(...) 拿 BM25 top-k
#   3) merge_hits(vec_hits, bm_hits, limit) 合并去重

import jieba
from rank_bm25 import BM25Okapi


def build_bm25(docs):
    """把所有块分词后建 BM25 索引。docs 是文本列表，必须和 chroma 里的顺序一致。"""
    tokenized = [list(jieba.cut(d)) for d in docs]
    return BM25Okapi(tokenized)


def bm25_search(bm25, docs, metas, query, k=10):
    """BM25 检索 top-k，返回 [(doc, meta, score)]，与向量 retrieve() 的三元组对齐。"""
    tokens = list(jieba.cut(query))
    scores = bm25.get_scores(tokens)
    idx = sorted(range(len(scores)), key=lambda i: -scores[i])[:k]
    return [(docs[i], metas[i], float(scores[i])) for i in idx]


def merge_hits(vec_hits, bm_hits, limit=10):
    """合并两路召回：按 (source, chunk) 去重，向量优先，不够再用 BM25 补。

    关键点：两路各自取多少、最后留多少，是两个独立参数。
    D12 实测：各取 5、留 8 时，#11 的 examples.md 排第 9 进不来；
    各取 10、留 10 才把它捞回来（recall@5 的 k 仍然算「前 5 条」，
    limit 是给模型的上下文条数，不是评分口径）。

    返回 [(doc, meta, third)]：third 对向量是距离、对 BM25 是分数。
    build_context 只用前两项，所以两种混在一起不会出错。
    """
    seen, out = set(), []
    for doc, meta, third in list(vec_hits) + list(bm_hits):
        key = (meta.get("source"), meta.get("chunk"))
        if key in seen:
            continue
        seen.add(key)
        out.append((doc, meta, third))
        if len(out) >= limit:
            break
    return out
