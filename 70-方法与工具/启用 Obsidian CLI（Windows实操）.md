---
tags:
  - 工作流
  - AI协作
created: 2026-10-16
---

# 启用 Obsidian CLI（Windows 实操）

## 一句话

CLI 打不开**不是设置没找到，是安装器太老**：应用更新只换 `obsidian-<版本>.asar`，**不生成 `Obsidian.com` 终端转发器**，那个文件只有用 1.12.4+ 的**官方安装器**装一遍才会有。

## 先看两个完全不同的版本号

这是整件事的关键，Obsidian 在 Windows 上有两个独立版本：

| 版本 | 含义 | 怎么查 | 本机实测 |
| --- | --- | --- | --- |
| **应用版本** | 界面和功能，存在 `%APPDATA%\obsidian\obsidian-<版本>.asar` | Obsidian 里看设置，或看这个文件名 | **1.14.4** |
| **安装器版本** | `Obsidian.exe` 这个可执行文件本身的版本 | 右键 `Obsidian.exe` → 属性 → 详细信息；或读 `ProductVersion` | **1.8.9**（！） |

**"设置里找不到 CLI 开关"就是因为这个**：1.8.9 的 exe 里根本没有 CLI 那段逻辑，而 in-app updater 只更新 asar、**从不替换 exe**。

## 为什么 `Obsidian.com` 这么要紧

Windows 的 `.com` 可执行格式**优先级高于 `.exe`**。终端里敲不带扩展名的名字时，`.com` 会先被命中——这是微软从 DOS 时代留下的兼容机制。

Obsidian 正是利用这一点，在安装目录里放一个 **`Obsidian.com` 转发器**（内容其实是 `Obsidian.exe` 的副本）：敲 `obsidian` 时先命中它，它把命令行参数转发给**正在运行**的 Obsidian 实例去处理。

没有它就等于 CLI 不存在：参数要么没人接，要么被 `explorer` 当文件关联处理掉。

## 操作步骤

### 1. 先确认应用已是 1.12.4+

本次实测 1.14.4，够用。这一步通常早就满足了。

### 2. 关掉 Obsidian

安装器要替换 `Obsidian.exe`，正在运行的进程锁着文件会装不干净。

### 3. 下载并运行官方安装器（关键一步）

- 页面：<https://obsidian.md/download>
- Windows 直链（1.14.4）：<https://github.com/obsidianmd/obsidian-releases/releases/download/v1.14.4/Obsidian-1.14.4.exe>
- 实测大小 `341,331,008` 字节（≈325 MiB），下载页写的是 `Obsidian-1.14.4.exe`
- **本机可直连**：该直链的 host 能走通（`Invoke-WebRequest -Method Head` 返回 200）
- 装的时候**路径选成现有的 `D:\Users\29021\AppData\Local\Programs\Obsidian`**，不要装出第二份

装完效果：`Obsidian.exe` 的版本号变成 1.14.4，**同目录出现 `Obsidian.com`**。

### 4. 启用 CLI

Obsidian → **设置 → 通用 → 高级（Advanced） → 命令行界面 / Command line interface** → 打开。

> 开关在"**高级**"那一组里，不在"通用"第一屏——这一步很容易找错，官方文档写的是 `Settings > General > Advanced`。

### 5. 注册到 PATH

同一个面板里点 **"设置 CLI 以便在终端中使用 / Set up CLI to work in the terminal"**（按钮是 `Register`），把 `obsidian` 注册进 PATH。看到成功提示后**重启终端**（新开的窗口才读得到新 PATH）。

Windows 上这一按钮的实测行为：读 `[Environment]::GetEnvironmentVariable('Path','User')`，把安装目录**追加**到用户 PATH（若已存在则返回 `Already registered in PATH`）。

### 6. 验证

```bash
obsidian version     # 看版本
obsidian help        # 列全部命令
obsidian             # 不带参数 = 进 TUI（有自动补全和反向搜索）
```

## 排错

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 设置里根本没有"命令行界面" | exe 还是旧版（本机 1.8.9） | 走第 3 步重装 |
| 有开关但敲 `obsidian` 报"找不到命令" | PATH 没注册 / 终端没重启 | 重开终端；还不行就手动把安装目录加进用户 PATH |
| 报 `Command line interface is not enabled. Please turn it on in Settings > General > Advanced.` | 开关没打开 | 回第 4 步 |
| 冒号子命令（`property:set name=…`）静默失败、exit code 127 | 老安装器 + `.com` 缺失时，Git Bash / PowerShell 可能错误命中 `.exe` | 重装安装器；或临时显式写 `Obsidian.com property:set …` |
| 说明里的注册按钮点了报错 "executable is ... instead of obsidian" | 程序会校验可执行文件名 | 用官方安装器重装，不要手动改 exe 文件名 |

## 一个前提

**CLI 必须让 Obsidian 正在运行**——它是"把命令转发给活着的实例"，不是无头工具。

需要无头操作时用另一条路：`notesmd-cli`（Yakitrak，Go 写，走文件系统，不需要 Obsidian 运行也不需要 Catalyst）。Scoop 安装：

```bash
scoop bucket add scoop-yakitrak https://github.com/Yakitrak/scoop-yakitrak.git
scoop install notesmd-cli
```

| 场景 | 用哪个 |
| --- | --- |
| 日常读写笔记、要 Obsidian 里立刻可见 | 官方 `obsidian` CLI |
| 装插件/主题、Bases、Tasks、Sync | 官方 CLI（只有它有） |
| 没开 Obsidian / 脚本 / CI | `notesmd-cli` |
| **不缺工具、只想让 agent 读写文件** | **都不用**，直接文件读写即可（见 [[AI与Obsidian的协作分工]]） |

## 本次实测记录（2026-10-17 凌晨，全部走通）

> **先明确用途**：这条 CLI 是**给 AI 用的**——目标是让 AI 能借 Obsidian 自己的索引做检索/反链/标签查询，再把该记的东西写进库。**人不需要敲这些命令**，这篇笔记主要是给 AI 看的复现记录，人只在这一步（装安装器）需要点一下。

本机安装目录：`D:\Users\29021\AppData\Local\Programs\Obsidian\`

### 实测结果

| 项目 | 结果 |
| --- | --- |
| `Obsidian.exe` 版本 | `1.8.9.0` → **`1.14.4.0`** |
| `Obsidian.com` | 之前不存在 → **已生成**（22,800 字节，文件版本 1.0.0.0） |
| 安装包 | `Obsidian-1.14.4.exe`，**341,331,008 字节**，sha256 `28662520368D5956DF7798076B8370AC730164A8863DCD4F678CED53F63FAA00` |
| `obsidian version` 输出 | `1.14.4 (installer 1.14.4)` |
| PATH | 用户级 PATH 末尾追加 `D:\Users\29021\AppData\Local\Programs\Obsidian` |
| CLI 开关的落盘位置 | `%APPDATA%\obsidian\obsidian.json` 里多出一个 **`"cli":true`** |
| `read` | ✅ 正常读回笔记正文 |
| `backlinks` | ✅ 新笔记的反链正确列出 `00-入口/库说明.md` |
| `search` | ✅ 命中 3 篇 |
| `tags sort=count counts` | ✅ `#工作流 3`、`#AI协作 3` |

### 复现要点

**1）下载卡在 github.com：** `github.com:443` 在这台机器上仍然是坏的（下载约 20 MB 后被 reset）。可行办法是**先拿 302 的 Location，再直连 CDN**：

```powershell
$u="https://github.com/obsidianmd/obsidian-releases/releases/download/v1.14.4/Obsidian-1.14.4.exe"
$r=Invoke-WebRequest -Uri $u -Method Head -MaximumRedirection 0 -SkipHttpErrorCheck
$loc=$r.Headers['Location']          # -> https://release-assets.githubusercontent.com/...
curl.exe -L -C - -o "$env:TEMP\Obsidian-1.14.4.exe" $loc
```

签名 URL **约 1 小时后过期**，拿到就尽快下（`-C -` 断点续传）。校验大小是不是 `341331008` 即可。

**2）静默安装有效：** `Start-Process Obsidian-1.14.4.exe -ArgumentList '--silent'`。装完版本号直接变 1.14.4，`Obsidian.com` 出现；**安装器进程自身可能挂着不退**（本次如此），确认文件都换新之后直接杀掉即可，不影响结果。

**3）CLI 开关不必手点：** 开关对应的 IPC 就是 `sendSync("cli", true)`。用 `Obsidian.exe --remote-debugging-port=9222` 起一个实例，走 CDP 在渲染进程里执行：

```js
window.electron.ipcRenderer.sendSync("cli", true)   // 再 sendSync("cli", null) 读回校验
```

设置**立刻**写进 `obsidian.json`（不必等退出）。完事把带调试端口的实例关掉、正常重启一次，用 `sendSync("cli", null)` 复验仍是 `true` 就算稳了。这条路径以后要批量改本机 Obsidian 设置时可以复用。

> 安全提示：这个调试端口是**临时**开的，用完必须关掉——`--remote-debugging-port` 暴露的是完整渲染进程控制权。日常不要把调试端口写进快捷方式。

**4）注册 PATH 的手工等价物**（`Register` 按钮做的就是这件事，会先把用户 PATH 读出来做去重）：

```powershell
$inst = 'D:\Users\29021\AppData\Local\Programs\Obsidian'
$u = [Environment]::GetEnvironmentVariable('Path','User')
if (($u -split ';') -notcontains $inst) {
  [Environment]::SetEnvironmentVariable('Path', ($u.TrimEnd(';') + ';' + $inst), 'User')
}
```

注册完**已经开着的终端读不到新 PATH**，必须新开一个窗口。

## 相关链接

← [[AI与Obsidian的协作分工]]（为什么需要 CLI：连接层与整理层的分工）
→ [[AI当笔记架构师的工作方法]]（工具没就绪不阻塞流程设计：规范不依赖 CLI 也能建）
→ [[库说明]]（本库的目录结构与同步方式）
