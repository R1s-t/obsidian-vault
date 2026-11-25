---
type: eda
tags:
  - EDA操作
  - 踩坑
tool: iverilog / Verilator / Yosys / GTKWave
pdk:
created: 2026-11-10
---

# Verilog 仿真工具链

## 目标

在**没有任何硬件**的情况下，写完一段 Verilog 就能在几秒内知道它对不对：编译、跑完全部测试用例、打印哪一组错了、生成可视化波形。

这是后面所有数字设计（加法器 → ALU → 五级流水 CPU → 一生一芯）的地基。没有它，验证只能靠焊板子或用万用表量，反馈周期从两秒变成几小时。

## 环境

- 系统：Windows 11 + **WSL2 里的 Ubuntu 24.04**（不是 22.04，理由见"踩过的坑"）
- 用户：`ris-t`，家目录 `/home/ris-t`
- 工具全在 `/usr/bin/` 下

## 为什么必须在 Linux 上做

三个理由，按重要性排：

1. **这些工具没有可用的 Windows 版**。`winget` 搜 iverilog / verilator / yosys / gtkwave 全部无结果；官方安装包会被 Defender 判为威胁（见坑 1）。
2. **工业界就是这么干的**。Cadence、Synopsys、Siemens EDA 全跑在 Linux 上。现在熟悉这套环境，等于提前适应实习和工作的日常。
3. **脚本化**。Makefile、tcl、bash 这套自动化在 Linux 上是原生的，在 Windows 上要绕一大圈。

## 六个包，各管一段

| 包 | 作用 | 什么时候用到 |
|------|------|------|
| `build-essential` | gcc / g++ / make / libc 头文件。**是元包**，会拉十几个包进来 | Verilator 把 Verilog 翻成 C++，得靠 g++ 编译；`make` 用来一键跑流程 |
| `git` | 版本控制 | 每次改代码留快照；往 GitHub 放作品 |
| `verilator` | **主力仿真器**。把 Verilog 翻译成 C++ 再编译成可执行文件 | 跑大仿真（几百万条指令）、严格 lint。一生一芯全程用它 |
| `iverilog` | 轻量仿真器，解释执行（配 `vvp`） | 第一遍调代码，报错好懂 |
| `gtkwave` | 波形查看器，读 `.vcd` | 看"进位晚了一拍""复位没生效"这类时序问题 |
| `yosys` | 综合：Verilog → 门级网表 | 回答"这段代码要多少个门、关键路径多长" |

## 流水线

```
你的 .v 源码
   │
   ├─ iverilog ──▶ .vvp ──▶ vvp 跑 ──▶ 文字结果 + .vcd
   │                                        │
   ├─ verilator ──▶ C++ ──▶ g++ 编译 ──▶ 可执行 ──▶ 同上
   │            └─────── 依赖 build-essential 的 g++/make
   │
   ├─ yosys ──▶ 门级网表（多少个门、多长延迟）
   │
   └─ git ──▶ 版本历史（跟仿真无关，管"你改了什么"）
                          │
                    gtkwave ◀── .vcd 画成时序图
```

**为什么装两个仿真器**：两者结论一致才说明代码本身对，而不是碰巧迎合了某一个工具的行为。`iverilog` 宽容、`verilator` 严格，先过前者再过后者的顺序能省时间。

## 步骤

1. **装 WSL + Ubuntu 24.04**（管理员 PowerShell）
   ```powershell
   wsl --install -d Ubuntu-24.04
   ```
   → 预期：第一次跑完提示"重启后生效"，**重启后再跑一遍**才会下载发行版。

2. **装工具链**（Ubuntu 终端里）
   ```bash
   sudo apt update
   sudo apt install -y build-essential git verilator iverilog gtkwave yosys
   ```
   → 预期：300–400 MB 下载，最后回到 `ris-t@CaoKang:~$`

3. **验证**（逐条敲，一条一行）
   ```bash
   iverilog -V | head -1
   verilator --version
   yosys -V
   gtkwave --version
   ```

4. **跑一个最小闭环**（造个空模块，确认整条链通）
   ```bash
   printf 'module t;\n  initial $display("iverilog works");\nendmodule\n' > /tmp/t.v
   iverilog -o /tmp/t.vvp /tmp/t.v && vvp /tmp/t.vvp
   ```
   → 预期：打印 `iverilog works`

## 验证清单

- [ ] `iverilog -V | head -1` 打印 `Icarus Verilog version 12.0`
- [ ] `verilator --version` 打印 5.0 以上（24.04 是 5.020）
- [ ] `yosys -V` 打印 `Yosys 0.33`
- [ ] `gtkwave --version` 打印 `GTKWave Analyzer v3.3.116`
- [ ] 最小闭环打印 `iverilog works`
- [ ] `wsl --list --verbose` 显示 `VERSION 2`

## 踩过的坑

**坑 1：Windows 原生装 iverilog 被 Defender 杀掉**

症状：下载 `iverilog-v14-*-x64_setup.exe`（25.8 MB，等了 130 秒），装完不到 20 秒 Defender 实时保护判定为威胁（ThreatID 2147927547）；连 `Get-FileHash` 都报

```
无法成功完成操作，因为文件包含病毒或潜在的垃圾软件
```

原因：Icarus 是老牌开源工具（无害），但安装包没有签名，Defender 的启发式规则误判。

→ 解决方案：**不要在 Windows 上硬装，走 WSL**。这条路本身也是对的（见"为什么必须在 Linux 上做"）。

---

**坑 2：装了 22.04 会拿到旧版 Verilator**

原因：Ubuntu 22.04 的 apt 源里 Verilator 是 **4.038**，不支持 `--binary --timing`（这两个选项 5.0 才有），跑现代 testbench 会直接报错。

→ 解决方案：**装 24.04**，里面是 5.020。选发行版时看的不是"哪个新"，而是"工具链版本够不够用"。

---

**坑 3：`iverilog -V` 第二行看起来像报错**

症状：

```
Icarus Verilog version 12.0 (stable) ()
Unable to get version from "/usr/lib/x86_64-linux-gnu/ivl/ivl -V -C"/tmp/..." -C"/usr/lib/x86_64-linux-gnu/ivl/vvp.conf""
```

原因：12.0 的已知显示 bug——`-V` 会去调后端 `ivl` 汇报编译器版本，路径拼接写错了。

→ 解决方案：**忽略**。它只影响这行版本号的显示，不影响编译和仿真。

**由此得出一条判断习惯**：输出里有报错字样，不等于工具坏了。要看它拦住的是"我要做的事"（必须修），还是它自己在自检时说了句怨话（记下即可）。

---

**坑 4：完全在 Ubuntu 里，就不要敲 `wsl`**

症状：在 Ubuntu 终端敲 `wsl --list --verbose` 得到 `wsl: command not found`。

原因：`wsl` 是 **Windows 侧**的管理命令，Linux 里当然没有。

→ 解决方案：看提示符区分在哪一侧。

```
ris-t@CaoKang:~$     ← Linux（$ 普通用户，# root）
PS C:\Users\29021>   ← Windows PowerShell
```

---

**坑 5：WSL 用户名别用纯数字**

原因：`9021` 这种名字 Linux 能存，但很多工具会把它当 **UID（用户编号）** 解析而不是用户名，`chown`、`ps -u`、`su`、`rsync` 都可能"看不见"这个用户；而且它还会出现在 `/home/9021`、Git 提交信息、Makefile 的家目录路径里。

→ 解决方案：小写字母开头，只用 `a-z 0-9 -`。名字一旦建好，后面改要动 `usermod` + 搬 `/home` + 修 sudoers，代价比当场改大三倍。

## 有用命令

| 命令 | 作用 |
|------|------|
| `verilator --lint-only x.v` | 只查语法和可综合性，不仿真 |
| `verilator --binary --timing tb.v dut.v` | 直接编译成可执行并运行 |
| `iverilog -o out.vvp *.v && vvp out.vvp` | 编译 + 跑 |
| `gtkwave dump.vcd` | 打开波形 |
| `yosys -p "read_verilog x.v; synth; stat"` | 综合并打印资源统计 |
| `wsl --list --verbose` | （Windows 侧）看发行版和 WSL 版本 |

## 链接

→ 后续：[[Linux 命令行速查]]
→ 首个练习：周任务单 W01 的「手写 4 位行波进位加法器」（代码自己写）
→ 域入口：[[库说明]]