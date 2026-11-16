---
type: eda
tags:
  - EDA操作
  - 踩坑
tool: iverilog
created: 2026-11-12
---

# Verilog 起步踩坑清单

## 目标

第一次手写 Verilog（1 位全加器 `full_adder`），从建文件到 `iverilog` 返回 0 之间踩到的六个坑。留档是为了下次不重复，也是给别人学时的最短路径。

## 环境

- 工具：Icarus Verilog 12.0（`/usr/bin/iverilog`）+ `vvp` + GTKWave 3.3.116
- 系统：WSL2 Ubuntu 24.04，工作目录 `~/projects/digital-lab/01-adder4/`
- 加载命令：无需加载，命令行直接调

## 九个坑

### 1. 文件名里的连字符和下划线

**症状**

```
$ iverilog -o /tmp/t.vvp full_adder.v
full_adder.v: No such file or directory
No top level modules, and no -s option.
```

**原因**：实际建的文件叫 `full-adder.v`（连字符），编译时写的是 `full_adder.v`（下划线）。Linux 里 `-` 和 `_` 是两个完全不同的字符，不是同一个字符的两种写法。

第二行 `No top level modules` 是**连带报错**——文件都没读到，自然没有模块可编译。这种抱错别看，看上面那行。

**解法**：`mv full-adder.v full_adder.v`。以后文件名一律用 `Tab` 补全，不手打。

**怎么确认是哪个字符**

```bash
sed -n '3p' full_adder.v | od -c   # 逐字节显示，下划线是 0x5F，连字符是 0x2D
grep -n -- "-" full_adder.v        # 列出所有含连字符的行
grep -n "_" full_adder.v           # 列出所有含下划线的行
```

### 2. 模块名里不能有连字符

`module full-adder` 是语法错误。Verilog 标识符只允许 `[a-zA-Z_][a-zA-Z0-9_$]*` 且不能数字开头，`-` 会被当成减号。

### 3. 报错行号不等于错误行号

```
full-adder.v:14: syntax error
I give up.
```

第 14 行是 `endmodule`，真正的错在**第 13 行末尾补一个分号就解决了**。Verilog 解析器顺序往下读，读到某处才发现"前面少了个东西"，于是把行号报在发现的地方。

`I give up.` 是 iverilog 的自嘲，等于"解析不下去了"。

### 4. 分号规则：语句要，块不要

```verilog
module full_adder (      ← 不要
    input  a,            ← 逗号
    output cout          ← 最后一个端口不加逗号
);                       ← 分号（端口列表结束）
    assign sum = ...;    ← 分号
endmodule                ← 不要
```

口诀：`assign` 是**语句**给分号；`module…endmodule`、`initial…end` 是**块**不给。

### 5. 名字写错不报错，会变成隐式 wire

```verilog
assign sum = a ^ b ^ c;    // 端口叫 cin，这里写成 c
```

`c` 从未声明，但 Verilog 不会拒绝，而是自动造一根 1 位 `wire` 叫 `c`——编译通过，仿真时它恒为 `x`（未知）。

**这比语法错误难查得多**，因为编译器没拦。所以要盯 `warning: implicit wire`。

### 6. 运算符优先级会把式子读成另一个意思

```verilog
assign cout = a & b | a | b & cin;      // ✗ 实际算的是 (a&b) | a | (b&cin)
assign cout = (a&b) | ((a|b) & cin);    // ✓
```

优先级从高到低：`~` > `&` > `^` > `|`。

宁可多写括号——综合出来是同一个电路，少写就是给自己埋雷。

### 7. `vvp` 是命令，`.vvp` 是文件名

```
$ vpp tb.vvp
vpp: command not found
```

| | 是什么 | 谁规定的 |
|---|---|---|
| `vvp` | **可执行程序**，在 `/usr/bin/vvp` | 装 iverilog 时装好的 |
| `.vvp` | **文件后缀**，纯惯例 | 你自己起的，叫 `tb.abc` 也能跑 |

`iverilog -o 输出文件名 源文件...` 里的输出名随便起；但 `vvp` 那个命令名一个字母都不能错。

`which vvp` 可以确认它在 `/usr/bin/vvp`。

### 8. `c3` 和 `c[3]` 不是一个东西

```verilog
wire c1, c2, c3;

.cout(c3)    // ✓ 一根叫 c3 的线
.cout(c[3])  // ✗ c 根本没声明，方括号是"取向量 c 的第 3 位"
```

- `c3`：标识符的一部分，字母 c 后面跟数字 3，**整体是名字**
- `c[3]`：**位选**，从名为 `c` 的向量里取第 3 位

`c` 不存在时又触发隐式 wire（见坑 5），编译器只给 warning，然后连接默默断掉。

### 9. 命名端口连接必须一字不差

```verilog
full_adder u3 (.a(a[3]), .b(b[3]), .c(c3), ...);   // ✗ 端口叫 cin，不叫 c
```

```
adder4.v:26: error: port 'c' is not a port of full_adder
```

点号后是**被例化模块内部**的端口名，必须和那个模块的 `module` 头完全一致。拼错就报 `is not a port`——这个错至少会报出来，比坑 5 和坑 8 好查。

## 一条更根本的认知

**编译通过 ≠ 电路正确。**

`iverilog` 只查语法（拼写、分号、括号配对），不查逻辑。`cout` 里写 `&` 还是 `|`，编译器一律放行。逻辑对不对，只有 testbench 能回答。

## 验证清单

- [x] `iverilog -o /tmp/t.vvp full_adder.v` 返回 0
- [x] testbench 8 组穷举全对（2026-11-13）
- [x] `adder4.v` 四个全加器串联，源码无 `+`
- [x] testbench 512 组穷举全过（`vvp tb.vvp | wc -l` 返回 513，2026-11-16）
- [x] Icarus 与 Verilator 双仿真都过（两工具输出 `diff` 逐字节一致）
- [x] 波形能在 GTKWave 里看到 `cin → c1 → c2 → c3 → cout`

## 有用命令

| 命令 | 作用 |
|---|---|
| `iverilog -o t.vvp a.v b.v` | 编译；`-o` 指定输出，第一个文件当顶层 |
| `vvp t.vvp` | 执行编译产物，这时才真的跑仿真 |
| `echo $?` | 看上一条命令退出码：0 成功，非 0 失败 |
| `iverilog ... && echo OK` | 成功才打印，等价于查 `$?` |
| `cat -n x.v` | 带行号看内容 |
| `sed -n '3p' x.v \| od -c` | 逐字节看某一行，区分 `-` 和 `_` |
| `which 命令` | 查命令实际路径 |

## 相关链接

← 环境搭建：[[Verilog 仿真工具链]]
← 命令行基础：[[Linux 命令行速查]]
→ 概念：[[全加器与进位生成-传播]]