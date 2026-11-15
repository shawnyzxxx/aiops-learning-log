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

## 第 2 步：跑一遍当天验收，拿到真数字

不要写「大概能跑」。用临时脚本在 venv 里实测，跑完删掉：

```bash
# 例：D9 的格式合法率
scp 临时脚本 root@192.168.223.129:/tmp/ && ssh ... 'cp /tmp/x.py /home/shawny/aiops/_tmp.py &&
  chown shawny /home/shawny/aiops/_tmp.py &&
  su - shawny -c "cd ~/aiops && source .venv/bin/activate && python _tmp.py";
  rm -f /home/shawny/aiops/_tmp.py'
```

## 第 3 步：把当天代码同步回仓库

```bash
scp root@192.168.223.129:/home/shawny/aiops/xxx.py src/xxx.py
md5sum src/xxx.py                                   # 与虚拟机 md5 比对，一致才算同步成功
ssh root@192.168.223.129 'md5sum /home/shawny/aiops/xxx.py'
```

- 仓库里放的是 **`src/`**，`corpus/`、`chroma/`、`*.log`、`.env` 已被 .gitignore，不要提交。
- 新增依赖要补 `src/requirements.txt`（带版本号 + 为什么需要）。

## 第 4 步：更新本地笔记（五处，一处都别漏）

| 文件 | 改什么 |
|---|---|
| `notes/D<NN>.md` | 当天复盘：做了什么 / 踩坑（含报错原文与根因）/ 重要发现 / 明天第一步 / 三行总结。数字全部来自第 1、2 步。**从 `notes/_每日模板.md` 复制时，保留开头那块「⚠️ 开工第一件事：激活虚拟环境」提醒，不要删** |
| `README.md` 进度表 | 打勾 + 一行成果 + 链接 |
| `src/README.md` | 进度表加一行、目录树加新文件、必要时补「怎么跑」 |
| `AIOps-3周速成-逐日清单.md` | 当天格子打勾，写实际数字；有遗留问题加 `- [!]` |
| `handbook/W2/W3-*.md` | **手册与实况不符就当场改**（例：D8 缺 pysqlite3 补丁、D9 缺 venv 激活提醒、D14 的 git 流程写错位置） |

## 第 5 步：提交推送

```bash
git add -A
git status --short                                  # 确认没有 .env / corpus / chroma / *.log
git commit -m "feat: 完成 D<NN> —— <一句话>

- 要点/踩坑条目"
git push                                            # origin = git@github.com:shawnyzxxx/aiops-learning-log.git
```

## 环境速查

| 项 | 值 |
|---|---|
| 虚拟机 | `192.168.223.129`（RHEL 9.6，root ssh 可进，项目属主 shawny） |
| 项目 | 虚拟机 `/home/shawny/aiops` ｜ Windows `C:\\Users\\28446\\Desktop\\找工作` |
| venv | `.venv`（Python 3.9.21）；**先 `source .venv/bin/activate` 再 `pip install`/`python`**，`which python` 自检 |
| 系统 python 陷阱 | 未激活时 `python` = `/usr/bin/python`，看不到 venv 包 → `ModuleNotFoundError` |
| 端口 | 8000 业务 / 8001 receiver / 9090 Prometheus / 9093 Alertmanager / 3000 Grafana |
| 网卡 | `ens33`（`localhost` 与本机 IP 走 `lo`，tc 加 ens33 测不出延迟） |
| git | 全局 `insteadof` 把 https 改写成 SSH；虚拟机**不是** git 仓库，代码在 Windows 提交 |
| 快照 | `base-ready` / `week1-done` / `week2-done`（D14 打） |
