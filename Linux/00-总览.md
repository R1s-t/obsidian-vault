---
tags:
  - Linux
aliases:
  - Linux
created: 2026-11-10
---

# Linux · 总览

> 它主要是一张工作台，并非一门课。EDA 工具、编译、版本控制、远程服务器，全都跑在这上面。

## 为什么单独一个域

微电子要用的工具——Verilator、Yosys、OpenROAD、Virtuoso、Calibre——**只有 Linux 版**。能不能在 Windows 上装上并非重点；重点是工业界没有人用 Windows 跑完整流程。

所以 Linux 是**入门必要条件**，并非“顺便学一学”的内容。

## 现有笔记

| 笔记 | 讲什么 | 什么时候用 |
| --- | --- | --- |
| [[Linux 命令行速查]] | 目录树、十条命令、权限、nano 与 vim、管道重定向 | 每天；忘了就查 |
| [[WSL 资源与磁盘]] | WSL2 是虚拟机、内存 / swap / 磁盘怎么分、`.wslconfig` 怎么调 | 仿真报 `Killed`、C 盘莫名变少、宿主机变卡时 |

## 在别的域里的相关笔记

| 笔记 | 在哪 | 为什么不在这个域 |
| --- | --- | --- |
| [[Verilog 仿真工具链]] | `EDA与工具链/4-开源EDA(Yosys-OpenROAD-KLayout)` | 主体是 EDA 工具，装它才用到 WSL |
| [[Obsidian 配置指南]] | `软件工具/` | 与微电子无关 |

## 以后会加什么

- `Shell 脚本入门` —— 批量跑仿真，`make` 不够用时
- `Makefile 与构建` —— 每个项目都要一个
- `WSL 与 Windows 文件互操作` —— 文件该放哪、为什么不要跨 `/mnt/c` 编译
- `远程服务器与 SSH` —— 一生一芯后期可能在远程机器上跑

## 本机环境备忘

| 项 | 值 |
| --- | --- |
| 发行版 | Ubuntu 24.04 LTS on WSL 2 |
| 用户名 | `ris-t` |
| 家目录 | `/home/ris-t` |
| 项目目录 | `~/projects` |
| 已装 | Icarus 12.0 · Verilator 5.020 · Yosys 0.33 · GTKWave 3.3.116 |

> 换机器时照 [[Verilog 仿真工具链]] 重装，再照这张表核对一遍。