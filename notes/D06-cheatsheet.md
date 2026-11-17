# D6 · Linux 排查 cheat sheet

> 自己写的，不是抄的。四类问题：**CPU 高 / 端口不通 / 慢但 CPU 不高 / 服务起不来**。
> 原稿写在 `handbook/W1-第1周.md` 的 D6 节，这里整理成可长期用的版本。

---

## {CPU 高}

**看**：`top` 里的 `%Cpu(s)`（重点看 `us` / `sy` / `wa`）和 `load average`

**异常**：

- `us` 高 = 用户态占用高，通常是应用在疯狂计算（死循环等）
- `sy` 高 = 系统态占用高，频繁的系统调用（大量网络包处理、IO 操作）
- `wa` 高 = 等着 IO 的 CPU 占比高，说明 CPU 其实在等磁盘或网络
- `load average` 远大于 CPU 核心数 → 系统严重拥堵

**下一步**：

```bash
ps aux --sort=-%cpu | head -10     # 找进程
top -H -p <pid>                    # 找线程
```

---

## {服务连不上 / 端口不通}

**看**：

```bash
ss -tlnp | grep <端口>
# 或
netstat -tulnp | grep <端口>
```

**异常**：

- 没输出 = 服务没启动成功，或者没监听在这个端口
- 有输出但连不上 = 监听在 `127.0.0.1` 而不是 `0.0.0.0`，或者被防火墙拦了

**下一步**：

```bash
systemctl status firewalld        # 查防火墙
iptables -L -n                    # 云服务器还要查安全组
systemctl status <服务名>          # 查服务状态
```

---

## {系统慢但 CPU 不高}

**看**：`iostat -x 1` 的 `%util` 和 `await`，或者 `top` 里的 `wa`

**异常**：

- `%util` 接近 100% = 磁盘读写被打满
- `await` 数值很高 = 单次 IO 响应极慢

**下一步**：

```bash
df -h                # 是不是满了
iotop -o             # 需要 root，直接看谁在疯狂读写
pidstat -d 1         # iotop 没装时的替代
```

---

## {Python 脚本一跑就 ModuleNotFoundError}（项目环境类，不是系统故障）

**先分清**：报错停在 `import` 那一行 → 十有八九是**虚拟环境没激活**，不是包没装、也不是代码写错。

**看**：

```bash
which python          # /usr/bin/python = 没激活；~/aiops/.venv/bin/python = 正常
echo $VIRTUAL_ENV     # 空 = 没激活
ls ~/aiops/.venv/bin/python
```

**异常**：

- `ModuleNotFoundError: No module named 'pysqlite3' / 'chromadb' / 'fastapi'` → 用的是系统 python，它看不见 `.venv` 里的包
- `pip install xxx` 显示装好了、`import` 还是失败 → 那次 pip 也没激活，包漏进了 `~/.local/lib/python3.9/site-packages/`
- 报错行是 `__import__('pysqlite3')` 这种「补丁行」→ 别以为补丁写错了，它只是第一个碰到缺包的地方

**下一步**：

```bash
cd ~/aiops && source .venv/bin/activate
which python                     # 确认变成 .venv/bin/python
pip list | grep -i 包名           # 确认包真在 venv 里
python xxx.py
```

> 规矩：**先激活，再 pip install，再 python**。激活状态不跨终端保留，每个新终端都要重新 source。

---

## {服务起不来}

**看**：`systemctl status <服务名>`（active 状态 + 最后几行报错）

**异常**：

- 状态是 `failed`
- 日志提示 `address already in use`（端口被占）或 `permission denied`（权限不够）

**下一步**：

```bash
journalctl -u <服务名> -n 50 --no-pager -xe   # 看第一行报错，通常是根因
lsof -i:<端口>                                 # 谁占了端口
```

再看配置文件有没有语法错误（`nginx.conf`、`docker-compose.yml`）。

---

## {宿主机连不上虚拟机（SSH / MobaXterm 超时）}

**先分清三段**：宿主的虚拟网卡 → 虚拟机本身 → 虚拟机里的服务。断在哪一段，症状完全不同。

**看**（Windows 侧，按顺序，不要跳）：

```bash
ipconfig | grep -A4 VMnet8                                  # VMnet8 必须是 192.168.223.1
MSYS_NO_PATHCONV=1 route print | grep 192.168.223            # 有没有到这个网段的路由
timeout 6 bash -c 'exec 3<>/dev/tcp/192.168.223.129/22' && echo 22通 || echo 22不通
```

**异常与判读**：

| 看到什么 | 结论 | 下一步 |
|---|---|---|
| VMnet8 是 `169.254.x.x` | **宿主虚拟网卡丢了静态 IP**（最常见，本项目踩过） | 下面两条 `netsh` 恢复 |
| VMnet8 正常、22 端口不通 | 虚拟机没开机，或 IP 变了 | 看 `vmware-vmx.exe` 在不在；查 `C:\ProgramData\VMware\vmnetdhcp.leases` 里今天发的哪个 IP |
| 22 通但 ssh 报 `Connection refused` | 虚拟机里 sshd 挂了 | VMware 控制台里 `systemctl restart sshd` |
| `ping` 不通但 `ssh` 能进 | **正常**，RHEL 防火墙拦 ICMP | 别拿 ping 当判据 |

**下一步**（管理员权限执行；正确值抄自 VMware 自己的配置，不是猜的）：

```powershell
netsh interface ip set address name="VMware Network Adapter VMnet8" static 192.168.223.1 255.255.255.0
netsh interface ip set address name="VMware Network Adapter VMnet1" static 192.168.0.1 255.255.255.0
```

依据：`C:\ProgramData\VMware\vmnetdhcp.conf` 里 `host VMnet8 { hardware ethernet 00:50:56:C0:00:08; fixed-address 192.168.223.1; }`，`subnet 192.168.223.0 netmask 255.255.255.0`。

**本项目实录（2026-11-17）**：MobaXterm 连不上。虚拟机其实是开着的——`vmware-vmx.exe` 在跑、DHCP 在 17:14 还发了 `192.168.223.129` 的租约、`aiops-app` 和三个容器都 active。坏点在**宿主**：VMnet8 和 VMnet1 同时掉到 `169.254.x`，路由表里一条 `192.168.223.0/24` 都没有。跑完上面两条 `netsh` 立刻恢复。

顺带把虚拟机也改成静态 IP 了（原来是 DHCP，租期只有 1800 秒，重启就可能换 IP 又「连不上」）：

```bash
nmcli connection modify ens33 ipv4.method manual ipv4.addresses 192.168.223.129/24 \
  ipv4.gateway 192.168.223.2 ipv4.dns 192.168.223.2 ipv4.dns-search localdomain
nmcli connection up ens33
```

改前的配置备份在虚拟机 `/root/ens33-before-static.txt`，要回滚就 `nmcli connection modify ens33 ipv4.method auto` 再 `nmcli connection up ens33`。

---

## 在本项目里怎么用

这套 cheat sheet 直接对应你搭的这套系统：

| 场景 | 命令 |
|---|---|
| 8000 端口是不是在听 | `ss -tlnp \| grep 8000` |
| 占端口的进程谁管的 | `ps -o pid,ppid,args -p <PID>`，**父进程是 1 = systemd** |
| 业务服务日志 | `journalctl -u aiops-app -f` |
| 容器日志 | `docker logs grafana --tail 50` |
| 容器状态 | `docker ps -a` |
| 磁盘是不是满了 | `df -h /`（根分区 36G） |

**一个已经踩过的坑**：8000 端口「杀不死」——`Restart=always` 会让 systemd 3 秒内拉起。
看到「端口被占 + 父进程是 1」，答案永远是 `systemctl stop/restart`，不是 `kill`。
