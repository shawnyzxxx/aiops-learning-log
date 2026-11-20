# 找工作 · AIOps 三周速成

目标：三周做出一个**能演示、有评测数据**的 AIOps 最小闭环，用于简历与面试。

## 从这里开始

**如果你是零基础，先看手册：**

| 文件 | 内容 |
|---|---|
| [handbook/00-总览.md](handbook/00-总览.md) | 运维在干什么、AI+运维是什么、五个必懂名词、工具速查表 |
| [handbook/W1-第1周.md](handbook/W1-第1周.md) | D1–D7：写出一个会生病、能被观测、会报警的小系统 |
| [handbook/W2-第2周.md](handbook/W2-第2周.md) | D8–D14：带评测数据的运维知识库问答（RAG） |
| [handbook/W3-第3周.md](handbook/W3-第3周.md) | D15–D21：串成闭环、量化效果、包装面试 |

每一天都是同一结构：**今天的目标 → 为什么做 → 用什么工具 → 具体步骤（命令+解释）→ 你会看到什么 → 卡住了看这里 → 做完检查**。

## 目录

| 路径 | 用途 |
|---|---|
| `handbook/` | **零基础手册**（主教材，逐日展开） |
| `AIOps-3周速成-逐日清单.md` | 精简版任务清单（打勾用） |
| `scripts/rhel-setup.sh` | RHEL 9 环境一键初始化脚本 |
| `notes/` | 每日复盘（D01–D21） |
| `docs/` | dashboard 截图、架构图、录屏 |
| `eval/` | 评测集与打分结果（`questions.json` 完整版 / `eval_set.json` 严格口径输入 / `eval_set_d13.json` 等价来源口径 / `eval_result.json`、`eval_result_d13*.json` 实测结果） |

## 环境

| 项 | 值 |
|---|---|
| 虚拟机 | VMware Workstation 17，RHEL 9.6，2 vCPU / 4 GB / 40 GB |
| 地址 | `192.168.223.129`（NAT） |
| 宿主机项目 | `C:\Users\28446\Desktop\找工作` |
| 虚拟机项目 | `~/aiops` |

## 进度

- [x] 环境搭建（Docker 29.9.3 / Compose v5.7.0 / EPEL / 镜像加速器）
- [x] D1 服务 + `/metrics`（[src/app.py](src/app.py) · [notes/D01.md](notes/D01.md)）
- [x] D2 Prometheus + Grafana + 仪表盘（[src/monitoring/](src/monitoring) · [notes/D02.md](notes/D02.md)）
- [x] D3 结构化日志（[notes/D03.md](notes/D03.md)）
- [x] D4 告警链路（[notes/D04.md](notes/D04.md)）
- [x] D5 故障注入（[notes/D05.md](notes/D05.md)）
- [x] D6 Linux 排查四件套（[notes/D06-cheatsheet.md](notes/D06-cheatsheet.md)）
- [x] D7 第 1 周复盘（[notes/D07.md](notes/D07.md)）
- [x] D8 语料切分 + bge-m3 向量入库 + 检索验证（[src/build_index.py](src/build_index.py) · [notes/D08.md](notes/D08.md)）
- [x] D9 RAG 结构化问答 + pydantic 校验（[src/rag.py](src/rag.py) · [notes/D09.md](notes/D09.md)）— 格式合法 20/20，拒答 5/5
- [x] D10 20 条评测集 + 自检脚本（[eval/questions.json](eval/questions.json) · [src/d10_check.py](src/d10_check.py) · [notes/D10.md](notes/D10.md)）
- [x] D11 第一次评测：recall@5 = **0.867**（13/15）、拒答率 **1.0**（5/5）（[src/run_eval.py](src/run_eval.py) · [eval/eval_result.json](eval/eval_result.json) · [notes/D11.md](notes/D11.md)）
- [x] D12 第一次调优：500 字切分（179 块）+ BM25 混合检索 → recall@5 = 0.867、**recall@10 = 0.933**、拒答率 1.0（[src/hybrid.py](src/hybrid.py) · [notes/D12.md](notes/D12.md)）
- [x] D13 第二轮调优 + 封装：外加等价来源口径 → recall@5 **0.867（严格）/ 0.933（等价来源）**、recall@10 **1.0**、拒答率 1.0（[src/rag_service.py](src/rag_service.py) · [eval/eval_set_d13.json](eval/eval_set_d13.json) · [notes/D13.md](notes/D13.md)）
- [x] D14 冻结版本：重跑复现全部检索指标，最终数字见下方[评测结果](#评测结果)；代码 9 个 `.py` md5 与仓库逐个一致（[notes/D14.md](notes/D14.md)）
- [x] 第 2 周（D8–D14 全部完成）
- [ ] 第 3 周

## 评测结果

> 冻结日期 **2026-11-20**。数字来自虚拟机 `~/aiops` 实跑，**不是估算**。细目见 [eval/eval_result.json](eval/eval_result.json)。

| 指标 | 数值 | 口径 / 怎么测的 |
|---|---|---|
| 语料规模 | 16 篇文档 / **179** 个片段 | `cat corpus_stats.json` → `{"chunks": 179, "sources": 16}` |
| 评测集 | 20 题（15 有答案 + 5 陷阱） | `eval/eval_set.json`，`frozen_at = 2026-11-17` |
| **recall@5** | **0.867**（13/15） | 严格：只认 `expected_source` 单文件 |
| **recall@5** | **0.933**（14/15） | 等价来源：认 `expected_sources` 任一 |
| **recall@10** | **0.933**（严格）/ **1.0**（等价来源） | 与上一行同一份检索结果 |
| 拒答正确率 | **1.0**（5/5） | 5 条陷阱题全部正确说「不知道」 |
| 答案均分 | **1.933 / 2.0**（29/15） | 0/1/2 人工评分，D14 冻结时重新独立打分 |
| 生成成功 | **20/20** | `generation_ok`，无超时、无解析失败 |

**两个 recall@5 是同一份检索结果按两种口径算的**，不是两次不同的运行。报数时两个都要给：

- 只说 0.933 不说严格口径 0.867 → 选择性报数
- 只说 0.867 不说等价来源 0.933 → 没讲清评测集为什么这么定

唯一未命中的是第 11 题（`examples.md`，向量第 9 / BM25 第 8，融合后进 top10 不进 top5），
属于**语料缺 PromQL 排除写法的例子**，不是检索算法问题。

## 三周验收标准

| 周 | 验收 |
|---|---|
| 周 | 验收 | 实际 |
|---|---|---|
| 第 1 周 | 能在 1 分钟内说清「系统健康吗，依据是哪三个指标」 | ✅ |
| 第 2 周 | recall@5 ≥ 0.8，5 条无答案样本至少 4 条正确拒答 | ✅ recall@5 **0.867 / 0.933**，拒答 **5/5** |
| 第 3 周 | 端到端能跑通，有 10 次注入实验的 MTTR 对比数据 | 进行中 |

## 三条铁律

1. 每周必须有一个能跑的东西，跑不起来就砍功能，不延期
2. 评测环节不可砍——没有数字，项目在面试里等于零
3. 任何需要 2 小时以上才能跑起来的工具，三周版一律不用

## 常用命令

``` bash
# 虚拟机里 —— 每次开新终端先跑这三行（激活状态不跨终端保留）
cd ~/aiops
source .venv/bin/activate
which python        # 自检：必须是 .venv/bin/python，否则后面全报 ModuleNotFoundError

uvicorn app:app --host 0.0.0.0 --port 8000     # 起业务服务
uvicorn receiver:app --host 0.0.0.0 --port 8001 # 起告警接收器
docker compose up -d                            # 起 Prometheus + Grafana + Alertmanager

curl -s localhost:8000/metrics | grep app_      # 看指标
jq 'select(.latency_ms > 500)' app.log          # 筛慢请求
python ops_helper.py analyze --alert HighLatency # AI 分析
```
