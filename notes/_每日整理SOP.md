# 每日整理 SOP · 上传仓库前必做

> 触发语：「整理上传」「同步笔记」「今天做完了」。
> 铁律：**先看虚拟机实况，再改本地笔记，最后才提交**。不要凭对话记忆写数字。

## 第 1 步：读虚拟机（唯一事实来源）

从 Windows 一条 ssh 批量采集，不要分多次：

```bash
ssh root@192.168.223.129 'bash -s' <<'REMOTE'
cd /home/shawny/aiops
ls -lt --time-style=+%m-%d\ %H:%M | head -20       # 今天改了哪些文件
stat -c '%y %n' rag.py build_index.py search_test.py 2>/dev/null
cat corpus_stats.json 2>/dev/null                    # 语料/块数
du -sh chroma 2>/dev/null                            # 索引体积
.venv/bin/pip list 2>/dev/null | grep -iE 'chromadb|openai|pydantic|dotenv|pysqlite|rank|jieba|fastapi|uvicorn'
sed 's/=.*/=<hidden>/' .env                          # 只看键名，绝不回显值
tail -40 /home/shawny/.zsh_history | sed 's/^: [0-9]*:[0-9]*;//'   # 今天真实敲过什么、报了什么错
systemctl is-active aiops-app.service; docker ps --format '{{.Names}}'
grep -c "\"ts\": \"$(date +%Y-%m-%d)\"" app.log 2>/dev/null     # 今天日志条数
REMOTE
```

要点：
- **`.zsh_history` 是踩坑来源**，报错、试错顺序都在这里，笔记里的「卡在哪」要按它写，不要编。
- **`.env` 只取键名**（`sed 's/=.*/=<hidden>/'`），任何情况下不把 key 写进笔记或仓库。
- 历史里的中文可能显示成乱码（如 `磁烻僦`），那是 zsh 历史编码问题，不是命令写错，别当坑记。
- **mtime 会骗人**：`chroma/chroma.sqlite3` 变新不等于重建了索引（查询也会写元数据）。判断有没有重建看 `corpus_stats.json` 的 mtime 最可靠。

## 第 2 步：跑一遍当天验收，拿到真数字

不要写「大概能跑」。用临时脚本在 venv 里实测，跑完删掉：

```bash
# 例：D9 的格式合法率
scp 临时脚本 root@192.168.223.129:/tmp/ && ssh ... 'cp /tmp/x.py /home/shawny/aiops/_tmp.py &&
  chown shawny /home/shawny/aiops/_tmp.py &&
  su - shawny -c "cd ~/aiops && source .venv/bin/activate && python _tmp.py";
  rm -f /home/shawny/aiops/_tmp.py'
```

临时文件用完要删干净（`/tmp/*.py`、`/tmp/*.json`、`~/aiops/_tmp.py`），别留在虚拟机里。

## 第 3 步：把当天代码同步回仓库

```bash
scp root@192.168.223.129:/home/shawny/aiops/xxx.py src/xxx.py
md5sum src/xxx.py                                   # 与虚拟机 md5 比对，一致才算同步成功
ssh root@192.168.223.129 'md5sum /home/shawny/aiops/xxx.py'
```

- 仓库里放的是 **`src/`**，`corpus/`、`chroma/`、`*.log`、`.env` 已被 .gitignore，不要提交。
- 新增依赖要补 `src/requirements.txt`（带版本号 + 为什么需要）。代码里 import 了就显式声明，别靠「随别的包侥幸带入」。

## 第 4 步：更新本地笔记（六处，一处都别漏）

| 文件 | 改什么 |
|---|---|
| `notes/D<NN>.md` | 当天复盘：做了什么 / 踩坑（含报错原文与根因）/ 重要发现 / 明天第一步 / 三行总结。数字全部来自第 1、2 步。**从 `notes/_每日模板.md` 复制时，保留开头那块「⚠️ 开工第一件事：激活虚拟环境」提醒，不要删** |
| `README.md` 进度表 | 打勾 + 一行成果 + 链接 |
| `src/README.md` | 进度表加一行、目录树加新文件、必要时补「怎么跑」 |
| `AIOps-3周速成-逐日清单.md` | 当天格子打勾，写实际数字；有遗留问题加 `- [!]` |
| `handbook/W2/W3-*.md` | **手册与实况不符就当场改**（例：D8 缺 pysqlite3 补丁、D9 缺 venv 激活提醒、D14 的 git 流程写错位置） |
| `handbook/*.md` 的「做完检查」 | 已打勾的条目补「标准答案」，规范见下一节 |
| `notes/_会话状态-*.md` | 进度、git 远端、产物表、踩坑表、下一步都要刷新到当天 |

## 「做完检查」标准答案怎么写

规则：**只给已打勾 `[x]` 的条目补答案**，缩进两格跟在条目下面，格式 `  **标准答案**：…`。
未做的 `[ ]` 保持空白，**不许提前填**。

**唯一例外**：「能解释：」类条目。它考的是能不能脱稿讲出来，答案本身就是学习材料，所以
**可以先给答案、勾留着**，并在答案末尾写「先自己说一遍再打勾」。等用户口述过一遍才打 `[x]`。
（D3 的「为什么要加 trace_id」、D9 的「为什么 temperature 要调低」都属于这类。）

内容要求（按优先级）：

1. **可验证的具体值**——命令 + 期望输出。写「`ss -tlnp | grep 8000` 有 LISTEN 行」，不写「服务正常」。
2. **失败时的第一排查方向**——写「没输出说明进程没起，不是防火墙」这种能省时间的判断。
3. **本机实测数字**——从第 1、2 步采集到的真值（130 块、距离 0.4117、格式合法 20/20），带日期。
4. **「能解释：」类条目给完整答案**——这是面试会追问的点，答案要能直接背出来，并说明反面场景（例如 temperature 调高适用在哪）。

不要写成笔记的复述，也不要留「略」。答案与实况冲突时，以虚拟机实测为准。

## 第 5 步：提交推送

```bash
git add -A
git status --short                                  # 确认没有 .env / corpus / chroma / *.log
git diff --cached --name-only | grep -iE '\.env|corpus|chroma|password|key'   # 空 = 安全
git commit -m "feat: 完成 D<NN> —— <一句话>

- 要点/踩坑条目"
git push                                            # origin = git@github.com:shawnyzxxx/aiops-learning-log.git
git status -sb | head -2                            # 确认 main...origin/main 无 ahead/behind
```

## 环境速查

| 项 | 值 |
|---|---|
| 虚拟机 | `192.168.223.129`（RHEL 9.6，root ssh 可进，项目属主 shawny） |
| 项目 | 虚拟机 `/home/shawny/aiops` ｜ Windows `C:\Users\28446\Desktop\找工作` |
| venv | `.venv`（Python 3.9.21）；**先 `source .venv/bin/activate` 再 `pip install`/`python`**，`which python` 自检 |
| 系统 python 陷阱 | 未激活时 `python` = `/usr/bin/python`，看不到 venv 包 → `ModuleNotFoundError`；pip 会把包漏进 `~/.local` |
| 端口 | 8000 业务 / 8001 receiver / 9090 Prometheus / 9093 Alertmanager / 3000 Grafana |
| 网卡 | `ens33`（`localhost` 与本机 IP 走 `lo`，tc 加 ens33 测不出延迟） |
| git | 全局 `insteadof` 把 https 改写成 SSH；虚拟机**不是** git 仓库，代码在 Windows 提交 |
| 快照 | `base-ready` / `week1-done` / `week2-done`（D14 打） |
| GitHub 连通 | git 走 SSH 直连即可；浏览器看网页/下 raw 需开 Clash（7897）或用 `gh-proxy.com` 前缀 |
