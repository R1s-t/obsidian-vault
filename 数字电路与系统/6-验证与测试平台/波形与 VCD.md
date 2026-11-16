---
type: concept
tags:
  - 概念卡片
  - Verilog
created: 2026-11-16
---

# 波形与 VCD

## 一句话

`$display` 回答「值对不对」，波形回答「**什么时候变的**」——后者才是硬件工程师真正盯的东西。

## 为什么需要它？

512 组穷举用 `$display` 能验完，但那个方法有个致命局限：**它是离散的**。

它只告诉你 `t=3.2μs 时 sum=1111`，不告诉你 `sum` 是怎么在几个门之间传过来的、`cout` 比 `cin` 晚了几级、进位链是不是真的逐级传递。

真实调试里，信号卡在 `x`、建立时间不够、两个信号竞争——这些**只能从波形上看出来**。

```verilog
$dumpfile("tb_adder4.vcd");
$dumpvars(0, tb_adder4);
```

两句，就能把仿真过程中每一根线的每一次变化都录进文件。

## 这两个不是 Verilog 语法

`$dumpfile`、`$dumpvars` 和 `$display`、`$finish` 一样，是**系统任务**（system task）。

| | 普通语句 | 系统任务 |
|---|---|---|
| 谁提供的 | Verilog 语言 | **仿真器** |
| 长相 | `assign`、`always`、`module` | `$` 开头 |
| 能综合成硬件吗 | 有的能 | **一律不能** |

`$` 就是标记：**看到 `$` 就知道这是仿真器在帮忙，不是电路的一部分。** 芯片上没有「存波形」这个门。

所以这两行只能出现在 testbench 里，绝不能出现在 `adder4.v` 或 `full_adder.v` 里。

## `$dumpfile("tb_adder4.vcd");`

给波形文件起名。

| 部分 | 说明 |
|---|---|
| `tb_adder4.vcd` | 文件名，字符串要引号 |
| `.vcd` | 惯例后缀，**不是必须** |
| 路径 | 相对于运行 `vvp` 时所在目录 |

一个模块只能有一个 `$dumpfile`，写两个后一个覆盖前一个。

**不写这行**：仿真照跑，但不生成文件——`$dumpvars` 没有「往哪写」的地址。

## `$dumpvars(0, tb_adder4);`

告诉仿真器**录哪些信号**。

```verilog
$dumpvars(0, tb_adder4);
//         ↑   ↑
//         |   从哪个模块开始（模块名，不是文件名）
//        层级深度
```

### 参数 1：层级深度

- **`0`** = 当前模块**及以下所有子层级**，到最底层
- `1` = 只有当前模块自己，子模块一根线都不录

本项目的层次：

```
tb_adder4          ← 第 0 层（a b cin sum cout i）
└── adder4 uut     ← 第 1 层（c1 c2 c3）
    ├── full_adder u0   ← 第 2 层
    ├── full_adder u1
    ├── full_adder u2
    └── full_adder u3
```

写 `0` → 三层全录，gtkwave 里能展开 `u0`~`u3`，看得见 `c1` `c2` `c3`。
写 `1` → 只录第 0 层，**`c1`~`c3` 在波形里根本找不到**。

**验收要看进位链的逐级传递，所以必须用 `0`。**

### 参数 2：模块名

- ✅ `tb_adder4` —— `module` 后面那个标识符
- ❌ `tb_adder4.v` —— 那是文件名，会报错

一个文件里可以有多个 module，仿真器认的是 `module` 声明。

## 为什么必须放在 `for` 循环之前

`initial` 块顺序执行。`$dumpvars` 一旦执行就开始「录音」。

放在循环之后：

```verilog
initial begin
    for (...) begin ... end
    $dumpvars(0, tb_adder4);   // ✗ 512 组跑完了才开始录
end
```

录到一片空白。

## 完整写法

```verilog
initial begin
    $dumpfile("tb_adder4.vcd");     // ① 起文件名
    $dumpvars(0, tb_adder4);        // ② 从这个模块起、录全部层级

    for (i = 0; i < 512; i = i + 1) begin    // ③ 跑激励
        {a, b, cin} = i[8:0];
        #10;
        $display(...);
    end
    $finish;                        // ④ 录音自动收尾
end
```

`$finish` 时仿真器自己把文件写完并关闭，不用手动「停录」。

跑法：

```bash
iverilog -o tb.vvp tb_adder4.v adder4.v full_adder.v && vvp tb.vvp > /dev/null && ls -lh tb_adder4.vcd
```

实测 512 组穷举产生 **29K** 的 `.vcd`。

## VCD 长什么样

`.vcd` = **V**alue **C**hange **D**ump。**纯文本**，能直接 `cat`。

```
$date
    Mon Nov 16 21:31:00 2026
$end
$timescale 1ns $end
$scope module tb_adder4 $end
$var reg 4 ! a [3:0] $end
$var reg 4 " b [3:0] $end
$var wire 4 # sum [3:0] $end
...
$enddefinitions $end
#0
b0 !
b0 "
#10
b1 "
```

| 记号 | 含义 |
|---|---|
| `$var` 行 | 信号声明：类型、位宽、**代号**、名字 |
| `#0` `#10` | 时间戳，单位由 `$timescale` 定 |
| `b1010 !` | 代号 `!` 的信号值变成 `1010` |

### 两个设计要点

**只记变化。** 没变化的时间段不占空间——否则 512 组每个时刻都存一遍，文件会大一个数量级。

**用单字符代号。** 真实波形几万个信号，每次写全名会让文件爆炸；声明区写一次对应关系，后面全用 `!` `"` `#`。

## gtkwave 怎么用

```bash
gtkwave tb_adder4.vcd &
```

`&` 放后台——它是图形程序，不加会占住终端。

| 区域 | 内容 |
|---|---|
| 左：SST 层次树 | `tb_adder4` → `uut` → `u0`~`u3` |
| 中：信号列表 | 点哪个层次，就显示那层的信号 |
| 右：波形区 | 拖进去的信号在这里画出来 |

**加信号**三选一：双击 / 拖拽 / Ctrl+多选后右键 `Recursive Add to Wave`。

推荐顺序（就是进位链的顺序）：

```
cin
uut.c1
uut.c2
uut.c3
cout
```

| 操作 | 快捷键 |
|---|---|
| 时间轴放大 | `+` 或 `Ctrl`+滚轮上 |
| 缩小 | `-` |
| 适应全宽 | `Shift`+`Ctrl`+`F` |
| 平移 | 按住中键拖 |

## 一个必须提前知道的预期

**`cin`、`c1`、`c2`、`c3`、`cout` 会在同一时刻一起跳变，没有阶梯状延迟。**

这不是 bug。`assign` 是连续赋值，**默认零延迟**——它描述「连线关系」，不是「门延迟 2ns 才翻转」。

真实芯片里确实每级有几十到几百皮秒延迟，但那要学 **静态时序分析（STA）**，用工艺库的延迟参数反标（SDF）才会体现在仿真里。

**所以第 4 条验收的正确看法不是「看延迟」，而是「看逻辑对应关系」。**

## 具体检查哪一段

跳到 `a=1111, b=0001, cin=0`（即 15+1）那一组：

| 位置 | 输入 | 输出 |
|---|---|---|
| u0 | a0=1, b0=1, cin=0 | sum0=0, **c1=1** |
| u1 | a1=1, b1=0, cin=c1=1 | sum1=0, **c2=1** |
| u2 | a2=1, b2=0, cin=c2=1 | sum2=0, **c3=1** |
| u3 | a3=1, b3=0, cin=c3=1 | sum3=0, **cout=1** |

这一小段里 `c1` `c2` `c3` `cout` **应该全是 1**——进位一路顶到最高位。

若某段 `c1=1` 但 `c2=0`，说明进位链断了，那才是真 bug。

## Verilator 的差异

Icarus 的 `$dumpfile`/`$dumpvars` 直接可用；**Verilator 要额外加 `--trace`** 才有波形：

```bash
verilator --binary --timing --trace -j 0 -o tb_adder4 ...
```

而且支持度比 Icarus 弱、编译更慢。

**出波形就用 Icarus**，别跟 Verilator 较劲——它主攻高速验证（几十亿周期那种），波形追踪是次要功能。

## 我第一次搞错的地方

- 以为「录波形」是 Verilog 语言的功能，写在了 `adder4.v` 里。它是**系统任务**，只有仿真器认，综合工具会直接报错。
- 用过 `$dumpvars(1, ...)` 后疑惑「为什么找不到 c1」。层级深度 `1` 只录当前层，`c1` 在子模块里。
- 以为波形上能看到门延迟。`assign` 零延迟，同一时刻全部翻转，想看得等 STA。

## 链接

← 概念：[[testbench 与验证思维]]
← 结构：[[模块-端口-例化]]
← 环境：[[Verilog 仿真工具链]]
← 踩坑：[[Verilog 起步踩坑清单]]