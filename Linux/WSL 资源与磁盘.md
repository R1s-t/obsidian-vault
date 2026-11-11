---
tags:
  - Linux
  - WSL
created: 2026-11-10
---

# WSL 的资源是怎么分的

> 一句话：WSL2 是一台**动态分配的虚拟机**——内存按需增长、有上限、不预留；磁盘是一块**只增不减**的虚拟硬盘。

## 一、它到底是什么

| | WSL 1 | WSL 2 |
| --- | --- | --- |
| 本质 | 系统调用翻译层 | 真正的 Linux 内核，跑在 Hyper-V 轻量虚拟机里 |
| 内存 | 与 Windows 共用 | 虚拟机独立分配，与 Windows 隔离 |
| 文件系统 | 直接用 Windows 的 | 独立的 ext4 虚拟硬盘 |

我们装的是 WSL 2，所以里面有一个**真的 Linux 内核**——这也是 EDA 工具能跑的原因（它们要的是内核，不是"像 Linux"）。

```
Windows（宿主机，15.8 GB）
  └─ Hyper-V 轻量虚拟机（WSL2）
       └─ Linux 内核        ← 看到 7.6 GB "物理"内存
            └─ 你的进程（iverilog / verilator / yosys …）
```

Windows 任务管理器里那个 `Vmmem` 或 `vmmemWSL` 进程，就是这台虚拟机。**它和 Linux 里的 `free` 是同一块内存**，不是重复计算。

## 二、三个资源的默认规则

| 资源 | WSL2 默认 | 本机实际 |
| --- | --- | --- |
| 内存上限 | 物理内存的 **50%** | **7.6 GiB**（宿主 15.8 GB） |
| Swap | 内存上限的 **25%** | **2.0 GiB** |
| 磁盘 | 虚拟上限 1 TB | 1007 GB，实际只占 2 GB |

## 三、内存：动态，不预留

这是最容易误解的一点——**不是开机就切走 7.6 GB**。

- 启动时只占几百 MB
- 你跑一个吃 3 GB 的仿真，Linux 才向 Windows 要 3 GB
- 任何时候总量不超过 7.6 GB
- 你要的超过 7.6 GB 时，会先用 swap（2 GB），再不够就 **OOM Killer 直接杀进程**

所以「内存不够」的表现通常不是卡，而是**进程莫名其妙消失**，报 `Killed` 或 `std::bad_alloc`。

## 四、只涨不落

Linux 有个习惯：**空闲内存不浪费，全拿来当文件缓存**（`free` 里的 `buff/cache`）。编译一次，它缓存一堆 `.o`；你删了，缓存还留着——理由是"万一还要用"。

Windows 看不到这个意图，只看到虚拟机占了 6 GB 不还。时间一长宿主机开始卡。

两种处理：

```bash
# 临时：手动让 Linux 释放缓存（要 sudo）
sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
```

```powershell
# 彻底：让 WSL 空闲时自动还内存（WSL 2.0+）
wsl --shutdown
```

后者配合下面 `.wslconfig` 里的 `autoMemoryReclaim=gradual` 才是长期解。

## 五、虚拟机什么时候真正关闭

**关掉终端窗口，虚拟机不会立刻关，但约一分钟后就自己关了。**

实测（本机，`systemd=true`）：

| 时刻 | `vmmemWSL` |
| --- | --- |
| 命令刚跑完 | 1474 MB |
| 35 秒后 | 865 MB（缓存开始回收） |
| 65 秒后 | 830 MB，仍在运行 |
| 约 3 分钟后 | **不存在** |

所以"有 systemd 就一定常驻"是个错觉：WSL 会在最后一个会话退出后按 `vmIdleTimeout` 计时（默认 **60 秒**），时间到就把整台虚拟机——连同 systemd 和它的 68 个服务——**强制终止**。systemd 挡不住。

| 操作 | 虚拟机关不关 | 多久 |
| --- | --- | --- |
| 点窗口 X / 输入 `exit` | 会，自动 | 约 60 秒 |
| `sudo poweroff` | 会 | 秒级 |
| `wsl -t Ubuntu-24.04` | 会（只停这个发行版） | 秒级 |
| `wsl --shutdown` | 会（所有发行版） | 秒级 |

想立刻腾内存就 `wsl --shutdown`；不急的话关掉窗口，一分钟它自己走。

想改这个等待时间（毫秒），在 `.wslconfig` 里加：

```ini
[wsl2]
vmIdleTimeout=10000
```

## 六、磁盘：只增不减

虚拟硬盘文件在：

```
C:\Users\29021\AppData\Local\Packages\CanonicalGroupLimited.Ubuntu24.04LTS_79rhkp1fndgsc\LocalState\ext4.vhdx
```

**关键**：你在 Linux 里删文件，这个 `.vhdx` **不会变小**。空间被标记为"未使用"但 Windows 侧仍被占着。

处理方向（执行前先 `wsl --help` 确认自己的版本支持）：

```powershell
wsl --manage Ubuntu-24.04 --set-sparse true
```

或在关闭 WSL 后用 `diskpart` 的 `compact vdisk` 手动压缩。现在只占了 2 GB，暂时不用管——等哪天发现 C 盘莫名少了十几 G 再处理。

## 七、配置文件

WSL 的配置是**用户级全局**的，一个文件管所有发行版：

```
C:\Users\29021\.wslconfig
```

我们目前**没有这个文件**，全部走默认值。要调就新建：

```ini
[wsl2]
# 内存上限。物理内存 16 GB，给 Linux 8 GB，留 8 GB 给 Windows
memory=8GB

# Swap 大小
swap=4GB

# 空闲时把缓存慢慢还给 Windows（WSL 2.0+ 才有）
autoMemoryReclaim=gradual

# 处理器核数，默认是逻辑核数
# processors=8
```

改完**必须**重启虚拟机才生效：

```powershell
wsl --shutdown
```

> **上限不是预留**：写 `memory=8GB` 不会让 WSL 立刻占 8 GB，它只是"最多能要到 8 GB"。空闲时 `Vmmem` 只有几百 MB。
>
> **但也不要设太高**：16 GB 的机器给 12 GB 是个坏主意——某次大仿真把它顶满时，Windows 只剩 4 GB，连浏览器都卡。经验值 **50%–60%**（16 GB → 8–10 GB）。
>
> **打游戏或做重活前，一条 `wsl --shutdown` 比任何配置都干脆**：虚拟机关掉，内存整块还给 Windows，下次进只要几秒。

## 八、什么时候需要调

一个 4 位加法器的仿真连 10 MB 都用不到，现在**完全不用改**。真正吃内存的是后面这些：

| 阶段 | 大致占用 | 7.6 GB 够不够 |
| --- | --- | --- |
| 加法器、状态机、小模块 | < 100 MB | 够 |
| RV32I 五级流水 + Verilator | 1–2 GB | 够 |
| 带 SRAM 的 SoC 仿真 | 4–8 GB | **临界** |
| 综合大设计（Yosys / OpenROAD） | 8–16 GB | 不够，要调 |

判断信号：仿真报 `Killed`、`std::bad_alloc`、或者 `dmesg | tail` 里出现 `Out of memory: Killed process`。

## 九、检查命令

在 Ubuntu 里：

```bash
free -h                  # 内存与 swap 总览
df -h /                  # 磁盘用了多少
nproc                    # 分到几个核
dmesg | tail -20         # 有没有被 OOM 杀掉
```

在 Windows 里：

```powershell
wsl --status             # 默认发行版、版本
Get-Process vmmem*       # 虚拟机当前实际占用
```

## 十、四个坑

1. **改 `.wslconfig` 不重启不生效**——必须 `wsl --shutdown`，光关窗口没用
2. **`wsl --status` 在 PowerShell 里乱码**——GBK 与 UTF-8 的老问题，不影响功能
3. **`free` 里 `available` 才是能用的数**，别盯着 `free` 那一列慌
4. **内存给太多反而更卡**——上限高不等于快，Windows 被挤爆时整机都在等

## 相关

- 装工具链的完整步骤：[[Verilog 仿真工具链]]
- 命令忘了怎么用：[[Linux 命令行速查]]
- 回到域入口：[[Linux/00-总览|Linux 总览]]