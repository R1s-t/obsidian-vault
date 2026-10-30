---
type: eda
tags:
  - 踩坑
tool: Obsidian
created: 2026-08-04
---

# Dataview 表格解析冲突

## 症状

用 Obsidian 打开某些 Markdown 文件时，Dataview 弹出解析错误：

```
Dataview (inline field '>'): Error:
-- PARSING FAILED --------------------------------------------------
> 1 | >
    | ^
Expected one of the following:
'(', 'null', boolean, date, duration, file link, list, ...
```

错误信息显示为一大段，但鼠标点击编辑后消失——仅出现在**实时预览模式**下。

## 原因

Markdown 表格的分隔行如果夹杂空格（如 `| ------ | ----------- | ---- |`），Obsidian 可能无法正确识别表格结构。此时 Dataview 会越过表格的 inline code 保护，看到表格单元格内的裸字符（如 `=>`、`->`、`>>`），将其误解为行内字段（`key:: value`）并尝试解析，导致报错。

## 解决方案

**方案一**：表格分隔行使用标准格式，不加空格。

```
错误：| ------ | ----------- | ---- |
正确：|--------|-------------|------|
```

**方案二**：将表格改为列表格式，彻底绕开解析问题。

```markdown
- `=>` → `\implies` — 推出
- `->` → `\to` — 箭头
```

## 相关链接

← [[Latex-Suite-微电子片段速查]]
