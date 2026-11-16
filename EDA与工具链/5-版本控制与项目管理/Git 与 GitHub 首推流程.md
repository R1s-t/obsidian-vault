---
type: eda
tags:
  - EDA操作
  - git
tool: git
created: 2026-11-16
---

# Git 与 GitHub 首推流程

## 目标

把一个刚写完的项目目录变成 GitHub 上的公开仓库，包含 `.gitignore`、README、首提交、远程推送的完整链路。实测走通一遍：`digital-lab/01-adder4`（4 位行波进位加法器）。

## 环境

- 系统：WSL2 Ubuntu 24.04
- Git 2.x（Ubuntu 自带）
- 远程：GitHub，SSH 认证（见 [[SSH 密钥与 GitHub 认证]]）
- 工作目录：`~/projects/digital-lab/`

## 四个区域

改一个文件，到它出现在 GitHub 上，经过四站：

```
工作区            暂存区            本地仓库           远程仓库
(你的 .v 文件) → (git add) → (git commit) → (git push) → github.com
```

| 区域 | 存什么 | 用哪条命令推进 |
|---|---|---|
| 工作区 | 你正在编辑的文件 | `git add` |
| 暂存区 | 下次提交要包含的快照 | `git commit` |
| 本地仓库 | 所有历史（`.git/` 目录） | `git push` |
| 远程仓库 | GitHub 上的副本 | — |

**暂存区这一层是 Git 特有的**，很多人觉得多余——它的价值在于「挑着提交」：改了五个文件但只有三个相关，可以只 add 那三个。

## 步骤

### 1. 确认目录内容

```bash
cd ~/projects/digital-lab
ls -la
ls -la 01-adder4
```

先看清楚哪些是源码、哪些是产物。**这一步决定 `.gitignore` 怎么写。**

### 2. 初始化

```bash
git init
git config --global init.defaultBranch main
```

| 命令 | 作用 |
|---|---|
| `git init` | 在当前目录建 `.git/`，成为仓库。**你的文件一个字节都没动** |
| `init.defaultBranch main` | 让以后新建的仓库默认分支叫 `main`（GitHub 的惯例） |

Git 会提示默认分支是 `master`。那堆黄色 `hint:` **不是错误**。

### 3. 写 `.gitignore`

```bash
nano .gitignore
```

本项目的实际内容：

```
# 仿真产物
*.vvp
*.vcd

# Verilator 生成的中间文件和可执行文件
obj_dir/

# 编辑器备份
*.save
*~

# 系统垃圾
.DS_Store
```

**判断标准一句话：这个文件能不能从源码重新生成？** 能 → 忽略；不能 → 提交。

| 排除什么 | 为什么 |
|---|---|
| `*.vvp` | `iverilog` 的字节码，二进制 |
| `*.vcd` | 波形，几十 KB 到几百 MB，重跑就有 |
| `obj_dir/` | Verilator 的 596K 中间产物（`.o` `.a` `.cpp`） |
| `*.save` `*~` | 编辑器崩溃时留的备份 |

**提交进去的垃圾会永远留在历史里**，删了也还在（除非重写历史）。所以这一步比看起来重要。

### 4. 验证忽略是否生效

```bash
git status --short --ignored
```

| 标记 | 含义 |
|---|---|
| `??` | 未跟踪，**会提交** |
| `!!` | 被忽略，**不会提交** |

实测输出：

```
?? .gitignore
?? 01-adder4/
!! 01-adder4/obj_dir/
!! 01-adder4/tb.vvp
!! 01-adder4/tb_adder4.vcd
```

**一眼看出三样垃圾是否都排除干净。**

想看到文件级（而不是目录级）：

```bash
git add -A --dry-run
```

`--dry-run` 是演习，只打印「会加什么」，不真的加：

```
add '.gitignore'
add '01-adder4/adder4.v'
add '01-adder4/full_adder.v'
add '01-adder4/tb_adder4.v'
add '01-adder4/tb_full_adder.v'
```

**这五行对了再往下走。**

### 5. 写 README

结构四块：

````markdown
# digital-lab

用 Verilog 手写的数字电路练习集

## Projects

| Directory | Description | Status |
| --- | --- | --- |
| `01-adder4` | 4 位行波进位加法器 + testbench | 完成 |

## How to run

```bash
cd 01-adder4

# Icarus: 编译 + 仿真（跑完会生成 tb_adder4.vcd）
iverilog -o tb.vvp tb_adder4.v adder4.v full_adder.v
vvp tb.vvp > /dev/null

# Verilator: 交叉验证同一份 RTL
verilator --binary --timing -j 0 -o tb_adder4 tb_adder4.v adder4.v full_adder.v
./obj_dir/tb_adder4 | wc -l

# 看波形
gtkwave tb_adder4.vcd &
```

预期：512 组输入全部通过；`wc -l` 返回 513（512 行结果 + 1 行 `$finish` 提示）。

## Environment

- WSL2 + Ubuntu 24.04
- Icarus Verilog 12.0
- Verilator 5.020
- GTKWave 3.3.116
````

**三条硬要求**：

1. **「怎么跑」必须真能跑通**——自己照抄试一遍，别凭记忆写
2. **版本号查真值**，不写「最新版」
3. **不写学习心得**，写「实现了什么、怎么验证它是对的」

最后这点最关键。面试官看 README 只想知道三件事：**这是什么、能不能跑、做到哪了**。写「通过本项目我学习了 Verilog 的基本语法」会立刻暴露是学生作业。

### 6. 提交

```bash
git status
git add -A
git commit -m "add 4-bit ripple carry adder with testbench"
```

| 命令 | 作用 |
|---|---|
| `git status` | **提交前必看**，确认没有垃圾混进来 |
| `git add -A` | 全部加入暂存区（`-A` = all，含新增和删除） |
| `git commit -m "..."` | 存成历史节点，`-m` 后面是说明 |

**commit message 的写法**（Linus 定的惯例）：

| 规则 | 例子 |
|---|---|
| 祈使句、现在时 | `add ...` 不是 `added ...` |
| 小写开头 | `add` 不是 `Add` |
| 不用句号 | — |
| 50 字符以内 | — |
| 说清「做了什么」 | 不写 `update` / `fix` / `...` |

紧接着改分支名（如果前面没设 `init.defaultBranch`）：

```bash
git branch -M main
```

`-M` 是**强制**重命名（大写 M 遇冲突也改；小写 `-m` 会拒绝）。

### 7. 建远程仓库并推送

浏览器 `https://github.com/new`：

| 字段 | 填什么 | 关键 |
|---|---|---|
| Repository name | 和本地目录同名 | — |
| Public / Private | **Public** | 简历要能点开 |
| **Add a README file** | **不勾** | ← 勾了会和本地冲突 |
| .gitignore / license | None | 本地已有 |

```bash
git remote add origin git@github.com:R1s-t/digital-lab.git
git push -u origin main
```

| 部分 | 含义 |
|---|---|
| `remote add` | 给远程起别名 |
| `origin` | 惯例别名（意思是「源头」） |
| `git@github.com:用户名/仓库名.git` | SSH 地址 |
| `push` | 把本地提交送到远程 |
| `-u` | `--set-upstream`，**记住对应关系**，以后只敲 `git push` |
| `origin main` | 推到 origin 的 main 分支 |

成功：

```
 * [new branch]      main -> main
branch 'main' set up to track 'origin/main'.
```

## 关于「不勾 README」

勾了 GitHub 会先替你在远程建一个 commit。你本地再推会被拒：

```
! [rejected]        main -> main (fetch first)
error: failed to push some refs
hint: Updates were rejected because the remote contains work that you do not have locally.
```

它怕覆盖远程的东西。两条路：`git pull --rebase origin main` 合并（历史多一次别扭的提交），或者**删了重建**（干净）。

学习项目选后者。

## 改写最近一次提交

**没推送之前随便改**（历史是本地数据）。推送之后改会麻烦别人。

```bash
git commit --amend -m "正确的说明"
```

| 部分 | 含义 |
|---|---|
| `--amend` | **改写**最近一次提交，不是新增 |

**改写后哈希会变**（如 `e9ebd13` → `042e375`）——commit 对象内容含 message，内容变了哈希必然变。这是设计如此。

只改作者不动说明：

```bash
git commit --amend --reset-author --no-edit
```

已经推上去了要强推：

```bash
git push --force-with-lease
```

`--force-with-lease` 比 `--force` 安全：先检查「远程是不是还停在我上次看到的状态」，如果中途别人推了新东西会**拒绝**，不会把人家的提交冲掉。

## 验证清单

- [x] `git init` 后 `.git` 目录存在
- [x] `git status --short --ignored` 里 `obj_dir/`、`.vvp`、`.vcd` 全在 `!!` 行
- [x] `git add -A --dry-run` 只列出 5 个源文件 + `.gitignore`
- [x] 首提交 6 个文件（4 个 `.v` + `.gitignore` + `README.md`）
- [x] `git log --oneline --stat` 显示正确的说明和文件清单
- [x] 分支名是 `main`
- [x] `git push -u origin main` 成功，`main -> main`
- [x] GitHub 网页上 README 正常渲染，无 `obj_dir/`

## 踩过的坑

### 1. `.gitignore` 里 `*.vpp` 匹配不到 `*.vvp`

```
add '01-adder4/tb.vvp'     ← 本该被忽略的却出现了
```

`vvp` 是 Verilog 虚拟机名，`.vvp` 是它吃的字节码后缀。写成 `vpp`（两个 p）就匹配不到任何文件。

**查法**：

```bash
git check-ignore -v 01-adder4/tb.vvp
echo "退出码=$?"
```

| 结果 | 说明 |
|---|---|
| 输出路径 + 行号 + 规则 | 已忽略 |
| 什么都没有，退出码 `1` | **没被忽略** |

### 2. `commit -m "..."` 里真的敲了三个点

```
[master (root-commit) e9ebd13] ...
```

`...` 是我举例用的占位符，但 Git **不会挑错**，它把引号里任何字符串原样收下。

三个月后回头看完全不知道那次改了什么；面试官看到 `...` 第一印象是「这人不太在意」。

**修**：`git commit --amend -m "正确说明"`。

### 3. `Repository not found`

SSH 下只有三种可能：**仓库不存在 / 名字不对 / 不属于这个账号**。

实测踩的是第二种——把账号名 `R1s-t` 里的**数字 1** 读成了字母 `I`，写成了 `Risttt`。

**核对方法**：`git remote -v` 看地址，浏览器打开 `https://github.com/用户名/仓库名` 看地址栏。**地址栏里的名字才是真的。**

### 4. Topics 不能用空格分隔

```
Repository topics must start with a lowercase letter or number,
consist of 50 characters or less, and can include hyphens.
```

输入 `verilog digital-design risc-v` 被当成**一个** topic（含空格，非法）。

**Topics 之间按 Enter 分隔**，一个个输：

```
verilog [Enter]
digital-design [Enter]
risc-v [Enter]
```

| 规则 | 例子 |
|---|---|
| 只能小写 | `verilog` ✅ `Verilog` ❌ |
| 只能用连字符 | `digital-design` ✅ `digital_design` ❌ |
| 不以符号开头 | `verilog` ✅ `-risc` ❌ |

### 5. 仓库首页的 Releases / Packages 区块

GitHub 仓库 → About 齿轮 → 「Include in the home page」三个勾选框。

| 项 | 是 GitHub 的什么功能 |
|---|---|
| Releases | 打 tag 发版 |
| Deployments | CI/CD 部署记录 |
| Packages | 发布到 npm / Docker 等 |

**纯源码项目三个都没有**，勾上会显示三个空区块，显得没做完。全不勾。

## 有用命令

| 命令 | 作用 |
|---|---|
| `git init` | 建仓库 |
| `git config --global init.defaultBranch main` | 新仓库默认分支名 |
| `git status` | 工作区状态（完整版） |
| `git status --short --ignored` | 紧凑版，含被忽略的文件（`??` / `!!`） |
| `git add -A` | 全部加入暂存区 |
| `git add -A --dry-run` | **演习**，只打印会加什么 |
| `git check-ignore -v <路径>` | 查某文件为什么被/没被忽略 |
| `git commit -m "说明"` | 提交 |
| `git commit --amend -m "新说明"` | 改写最近一次提交 |
| `git branch -M main` | 强制重命名当前分支 |
| `git remote add origin <url>` | 加远程 |
| `git remote -v` | 看远程地址 |
| `git remote set-url origin <url>` | 改远程地址 |
| `git push -u origin main` | 推送并记住上游 |
| `git push --force-with-lease` | 安全强推 |
| `git log --oneline --stat` | 历史 + 每次改了哪些文件 |
| `git log --format="%h  %an <%ae>  %s"` | 哈希 / 作者名 / 邮箱 / 说明 |
| `git ls-remote origin` | 只列远程分支，不下载 |

## 相关链接

← 认证：[[SSH 密钥与 GitHub 认证]]
← 命令行基础：[[Linux 命令行速查]]
← 项目：[[波形与 VCD]]