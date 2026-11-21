# collector.py —— 收到告警后，自动收集排障需要的三类证据
import json
import os
import time
from datetime import datetime, timedelta

import requests

PROM = "http://localhost:9090"
APP_LOG = "/home/shawny/aiops/app.log"
WINDOW_MIN = 10          # 看告警前后 10 分钟


# ── 证据 1：指标 ─────────────────────────────────────────
QUERIES = {
    "QPS": 'sum(rate(app_requests_total[1m]))',
    "P95延迟(秒)": 'histogram_quantile(0.95, sum(rate(app_latency_seconds_bucket[1m])) by (le))',
    "5xx错误率": 'sum(rate(app_requests_total{status=~"5.."}[1m])) / sum(rate(app_requests_total[1m]))',
    "服务存活": 'up{job="aiops-app"}',
}


def query_metric(expr: str, minutes: int = WINDOW_MIN):
    """查过去 N 分钟的曲线，返回 [时间, 值] 列表"""
    end = time.time()
    start = end - minutes * 60
    r = requests.get(f"{PROM}/api/v1/query_range", params={
        "query": expr, "start": start, "end": end, "step": "30s",
    }, timeout=10)
    data = r.json()
    if data.get("status") != "success":
        return []
    result = data["data"]["result"]
    if not result:
        return []
    return result[0]["values"]          # [[时间戳, "值"], ...]


def summarize_series(values):
    """把一条曲线压成几个数字，别把 40 个点全塞给模型"""
    if not values:
        return {"状态": "无数据"}
    nums = [float(v) for _, v in values]
    return {
        "最小": round(min(nums), 4),
        "最大": round(max(nums), 4),
        "平均": round(sum(nums) / len(nums), 4),
        "最新": round(nums[-1], 4),
    }


def collect_metrics() -> dict:
    out = {}
    for name, expr in QUERIES.items():
        try:
            out[name] = summarize_series(query_metric(expr))
        except Exception as e:
            out[name] = {"状态": f"查询失败: {e}"}
    return out


# ── 证据 2：日志 ─────────────────────────────────────────
def collect_logs(minutes: int = WINDOW_MIN) -> dict:
    """取时间窗内的错误日志和慢请求，做聚合而不是全量返回"""
    if not os.path.exists(APP_LOG):
        return {"状态": "日志文件不存在"}

    cutoff = datetime.now() - timedelta(minutes=minutes)
    errors, slow, total = [], [], 0

    with open(APP_LOG, encoding="utf-8") as f:
        # 只读最后 5000 行，避免大文件拖死
        lines = f.readlines()[-5000:]

    for line in lines:
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = rec.get("ts", "")
        if ts and ts < cutoff.strftime("%Y-%m-%dT%H:%M:%S"):
            continue
        total += 1
        if rec.get("status", 0) >= 500:
            errors.append(rec)
        if rec.get("latency_ms", 0) > 500:
            slow.append(rec)

    return {
        "窗口内日志条数": total,
        "5xx条数": len(errors),
        "慢请求条数(>500ms)": len(slow),
        "5xx样例": errors[-3:],          # 只给 3 条样例，别塞爆上下文
        "慢请求样例": slow[-3:],
    }


# ── 证据 3：文档 ─────────────────────────────────────────
def collect_docs(alert_name: str) -> list:
    """用告警名去知识库里搜相关的排查步骤"""
    try:
        from rag_service import ask
        r = ask(f"{alert_name} 告警的排查步骤是什么")
        return [{"摘要": r["answer"][:400], "来源": r["citations"]}]
    except Exception as e:
        return [{"状态": f"检索失败: {e}"}]


# ── 汇总 ─────────────────────────────────────────────────
def collect(alert: dict) -> dict:
    name = alert.get("name") or alert.get("alertname") or "UnknownAlert"
    started = datetime.now()
    bundle = {
        "告警": {
            "名称": name,
            "级别": alert.get("severity", "unknown"),
            "摘要": alert.get("summary", ""),
            "触发时间": alert.get("time", started.isoformat(timespec="seconds")),
        },
        "指标": collect_metrics(),
        "日志": collect_logs(),
        "相关文档": collect_docs(name),
        "收集耗时秒": round((datetime.now() - started).total_seconds(), 2),
    }
    return bundle


if __name__ == "__main__":
    demo = {"name": "HighLatency", "severity": "warning", "summary": "P95 延迟超过 500ms"}
    print(json.dumps(collect(demo), ensure_ascii=False, indent=2))
