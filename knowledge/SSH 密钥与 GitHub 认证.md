---
type: eda
tags:
  - EDA操作
  - git
tool: ssh
created: 2026-11-16
---

# SSH 密钥与 GitHub 认证

## 目标

让 WSL 里的 `git push` 不用输密码，一次配好永久可用。

## 环境

- 系统：WSL2 Ubuntu 24.04（用户名 `ris-t`）＋ Windows 11 宿主
- 工具：OpenSSH（Ubuntu 自带）
- GitHub 账号：`R1s-t`

## 先分清两个名字

| 名字 | 是什么 | 在哪 |
|---|---|---|
| **`R1s-t`** | GitHub **账号名** | 决定仓库 URL：`github.com/R1s-t/...` |
| **提交作者名** | `git config user.name` | 只影响 `git log` 里显示的字符串 |

**URL 认账号名，不认 commit 作者名。** 这两者不一致时，`git push` 报 `Repository not found`——它去错的人名下找仓库了。

## 公钥和私钥

| 文件 | 是什么 | 能给别人吗 |
|---|---|---|
| `id_ed25519` | **私钥** | ❌ 绝对不行，等于银行卡密码 |
| `id_ed25519.pub` | **公钥** | ✅ 就是要贴到 GitHub 上 |

原理：私钥留在本机，公钥交给服务器。登录时服务器发一段挑战，你私下签名，它用公钥验。**全程私钥不离机。**

## 生成密钥对

```bash
ssh-keygen -t ed25519 -C "你的邮箱或标签"
```

| 部分 | 含义 |
|---|---|
| `ssh-keygen` | 生成密钥的程序 |
| `-t ed25519` | 类型。新算法，密钥短、快、比 RSA 安全 |
| `-C "..."` | 注释，纯标签，方便认 |

问三句全部回车（默认位置、不设 passphrase）。

> 不设 passphrase 是学习场景的取舍：设了更安全（密钥文件被偷也用不了），但每次 push 要输。

## 贴到 GitHub

```bash
cat ~/.ssh/id_ed25519.pub
```

复制**一整行**（`ssh-ed25519 AAAA... 标签`，一个字符都不能少）。

GitHub → 头像 → **Settings** → **SSH and GPG keys** → **New SSH key** → 粘贴 → Add。

## 配置 443 端口（国内关键）

22 端口在国内常被 RST。GitHub 提供了 443 入口 `ssh.github.com`。

`~/.ssh/config`：

```
Host github.com
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile ~/.ssh/id_ed25519_github
    IdentitiesOnly yes
```

| 行 | 含义 |
|---|---|
| `Host github.com` | 敲 `git@github.com` 时匹配这段 |
| `HostName ssh.github.com` | **实际连的主机**（443 专用入口） |
| `Port 443` | 走 443 不走 22 |
| `User git` | GitHub 的 SSH 用户名固定是 `git` |
| `IdentityFile` | 用哪把私钥 |
| `IdentitiesOnly yes` | 只用指定这把，不让 ssh 瞎试其他 key（试太多会被限流） |

## 验证

**一、先查配置解析对不对（不连接）**

```bash
ssh -G github.com | grep -E "^(hostname|port|user|identitiesonly)"
```

预期：

```
hostname ssh.github.com
port 443
user git
identitiesonly yes
```

**二、再真连**

```bash
ssh -T git@github.com
```

| 部分 | 含义 |
|---|---|
| `-T` | 不分配终端（GitHub 只做认证，不给 shell） |
| `git@github.com` | `用户名@主机` |

首次会问 TOFU：

```
The authenticity of host '[ssh.github.com]:443' can't be established.
ED25519 key fingerprint is SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU.
Are you sure you want to continue connecting (yes/no/[fingerprint])?
```

**这个指纹是 GitHub 官方的 ED25519 指纹。** 敲 `yes`（完整三个字母）。

成功：

```
Warning: Permanently added '[ssh.github.com]:443' (ED25519) to the list of known hosts.
Hi R1s-t! You've successfully authenticated, but GitHub does not provide shell access.
```

`does not provide shell access` **不是错误**——GitHub 不给你登录服务器，只用来推代码。

## TOFU 是什么

**T**rust **O**n **F**irst **U**se，首次使用即信任。

SSH 没有中心化证书机构，所以第一次连接把对方的「身份证号」（指纹）打给你，让你自己判断。判断完它记进 `~/.ssh/known_hosts`，之后自动比对：一致就静默通过，**不一致就拒绝并报警**——那说明有人在劫持流量。

所以那个指纹**一定要核对**，不能闭眼敲 yes。

## 为什么显示 `[ssh.github.com]:443`

SSH 规定：**端口不是默认的 22 时，主机名必须用方括号包起来**，否则冒号会被误认为端口的开始。

`[主机名]:端口` 是标准写法。`known_hosts` 里记的也是这个形式——所以以后改回 22 端口时会重新问一次（「主机标识」变了）。

## 跨环境复用（Windows ↔ WSL）

Windows 侧已有密钥（给 Obsidian 的 git 插件用），WSL 是独立环境看不到它。想让 WSL 复用：

```bash
mkdir -p ~/.ssh
cp /mnt/c/Users/<用户名>/.ssh/id_ed25519_github ~/.ssh/
cp /mnt/c/Users/<用户名>/.ssh/id_ed25519_github.pub ~/.ssh/

chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519_github
chmod 644 ~/.ssh/id_ed25519_github.pub
```

| 权限 | 含义 |
|---|---|
| `700` 目录 | 只有自己能进 |
| `600` 私钥 | 只有自己能读写（**必须**） |
| `644` 公钥 | 别人只能读 |

**`chmod` 这步不能省。** 从 `/mnt/c` 复制过来的文件继承 Windows 的宽松权限（常是 `777`），SSH 检测到「别人也能读私钥」会**直接拒绝使用**：

```
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@         WARNING: UNPROTECTED PRIVATE KEY FILE!          @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
Permissions 0777 for '/home/ris-t/.ssh/id_ed25519_github' are too open.
```

数字读法：三位分别是「自己 / 同组 / 其他人」，`4`=读 `2`=写 `1`=执行，相加。

**两个环境共用一把钥匙**的代价：将来轮换（换电脑、怀疑泄露）时两边都要换。

## 踩过的坑

### 1. 配置项拼错

```
/home/ris-t/.ssh/config: line 6: Bad configuration option: identitionly
/home/ris-t/.ssh/config: terminating, 1 bad configuration options
```

写成 `identitionly`，正确是 `IdentitiesOnly`（**Identities** 复数 + **Only**）。

`Bad configuration option` = ssh 不认识这个选项名，整个 config 判定无效，连接根本没发起。

**报错已经点名了行号和那个词**，照着核对拼写即可，不用猜。

> ssh 配置的选项名**不区分大小写**，`identitiesonly` 也认。错的是拼写，不是大小写。

### 2. 用户名里数字和字母混淆

`ssh -T` 输出 `Hi R1s-t!`，但肉眼读成了 `Risttt`（数字 `1` 像字母 `I`），于是 `git remote add` 写错用户名，`git push` 报：

```
ERROR: Repository not found.
fatal: Could not read from remote repository.
```

**`Repository not found` 在 SSH 下只有三种可能**：仓库不存在 / 名字不对 / 不属于这个账号。权限问题反而少见（`ssh -T` 已经证明身份了）。

修：

```bash
git remote set-url origin git@github.com:R1s-t/digital-lab.git
```

## 有用命令

| 命令 | 作用 |
|---|---|
| `ssh-keygen -t ed25519 -C "标签"` | 生成密钥对 |
| `cat ~/.ssh/id_ed25519.pub` | 看公钥内容 |
| `ls -la ~/.ssh` | 看有哪些密钥文件（`-a` 才能看到隐藏目录） |
| `chmod 600 私钥` | 修权限，SSH 强制要求 |
| `ssh -G github.com` | **不连接**，只打印解析后的最终配置 |
| `ssh -T git@github.com` | 测试认证 |
| `ssh -v -T git@github.com` | 带调试输出（`-v` 可叠加 `-vvv`） |
| `git remote -v` | 看远程地址 |
| `git remote set-url origin <新地址>` | 改远程地址 |
| `git ls-remote origin` | 只列远程分支，不下载 |

## 相关链接

→ 下一步：[[Git 与 GitHub 首推流程]]
← 命令行基础：[[Linux 命令行速查]]
← 环境：[[Verilog 仿真工具链]]