#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间表任务同步工具（轻量版）

只做两件事：
  week      按日期确保「本周任务单」存在；不存在就从时间表的逐周表生成骨架
  progress  扫描所有周任务单，算完成率，回填到时间表的自动区块

用法：
  python timeline.py                  # week + progress
  python timeline.py week --week 1    # 强制生成/检查第 1 周
  python timeline.py progress --dry   # 只看不写
  双击 同步时间表.cmd 等价于 python timeline.py

安全约定：
  - 只改写 <!-- AUTO:PROGRESS:START --> 与 <!-- AUTO:PROGRESS:END --> 之间的内容
  - 已有周任务单永不覆盖
  - 写盘前备份到库外 `ObsidianArchive/_backup/`（不占库，不进 git）
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------- 路径配置

TOOLS_DIR = Path(__file__).resolve().parent
VAULT = TOOLS_DIR.parents[1]                      # .../ObsidianVault
TS_DIR = VAULT / "1-时间表"                        # 时间表目录（改名只需改这一行）
WEEK_DIR = TS_DIR / "周"                           # 每周任务单
# 备份放在库外：历史快照不属于知识库，不该被 Obsidian 索引与同步
# 库在 ~/Documents/ObsidianVault，归档在 ~/ObsidianArchive（同在用户主目录下）
ARCHIVE_DIR = VAULT.parents[1] / "ObsidianArchive" / "_backup"
BACKUP_DIR = ARCHIVE_DIR

TIMELINE_GLOB = "*全周期时间表*.md"
PLAN_NAME = "项目规划.md"

W1_START = date(2026, 11, 9)                       # W1 的周一
TOTAL_WEEKS = 31

STAGE_NAME = {
    "P0": "P0 启动",
    "P1": "P1 寒假",
    "P2": "P2 春季",
    "P3": "P3 实习+暑假",
    "P4": "P4 初试",
    "P5": "P5 窗口二",
}

# 各阶段默认周工时；按周覆盖写在 WEEK_HOURS_OVERRIDE
STAGE_HOURS = {"P0": 15, "P1": 40, "P2": 20, "P3": 45, "P4": 0, "P5": 15}
WEEK_HOURS_OVERRIDE = {8: 5, 9: 5, 13: 25}         # 期末周、春节周

MARK_START = "<!-- AUTO:PROGRESS:START -->"
MARK_END = "<!-- AUTO:PROGRESS:END -->"

# 主任务拆分符：先按分号分段，再按斜杠/顿号/带空格的加号切（不切 C++ 这种）
SPLIT_MAJOR = re.compile(r"[；;]")
SPLIT_MINOR = re.compile(r"/|、|\s\+\s")

WEEK_ROW = re.compile(
    r"^\|\s*W(\d+)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|\s*$"
)
TASK_LINE = re.compile(r"^- \[( |x|X)\] ")
TASK_ID = re.compile(r"^- \[( |x|X)\] (W\d{2}-[A-Z]?\d+)")


# ---------------------------------------------------------------- 基础工具

def die(msg: str, code: int = 1) -> "NoReturn":  # type: ignore[valid-type]
    print(f"[错误] {msg}", file=sys.stderr)
    raise SystemExit(code)


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def write_text(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8", newline="\n")


def backup(p: Path) -> None:
    if not p.exists():
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]   # 带毫秒，同一秒内多次写也不互相覆盖
    dst = BACKUP_DIR / f"{p.stem}.{stamp}{p.suffix}"
    shutil.copy2(p, dst)


def frontmatter(text: str) -> dict:
    """极简 frontmatter 解析：只认 key: value 单行"""
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}
    fm = {}
    for line in lines[1:end]:
        if ":" in line and not line.startswith((" ", "\t", "-")):
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


# ---------------------------------------------------------------- 时间表解析

def find_timeline() -> Path:
    cands = [p for p in TS_DIR.glob(TIMELINE_GLOB) if p.is_file()]
    if not cands:
        die(f"在 {TS_DIR} 下找不到 *全周期时间表*.md")
    best, best_key = None, (-1, False)
    for p in cands:
        fm = frontmatter(read_text(p))
        try:
            ver = int(fm.get("version", "0") or 0)
        except ValueError:
            ver = 0
        key = (ver, fm.get("status", "").strip() == "current")
        if key > best_key:
            best, best_key = p, key
    return best


def parse_weeks(text: str) -> dict:
    """返回 {周号: {date, stage, task, milestone}}"""
    weeks = {}
    for line in text.splitlines():
        m = WEEK_ROW.match(line)
        if not m:
            continue
        n = int(m.group(1))
        weeks[n] = {
            "date": m.group(2).strip(),
            "stage": m.group(3).strip(),
            "task": m.group(4).strip(),
            "milestone": m.group(5).strip(),
        }
    if not weeks:
        die("时间表里没解析到逐周表（形如 | W1 | 11.09–11.15 | P0 | ... |）")
    return weeks


def week_range(n: int) -> tuple[date, date]:
    start = W1_START + timedelta(days=7 * (n - 1))
    return start, start + timedelta(days=6)


def week_hours(n: int, stage: str) -> int:
    if n in WEEK_HOURS_OVERRIDE:
        return WEEK_HOURS_OVERRIDE[n]
    return STAGE_HOURS.get(stage, 15)


def current_week(today: date | None = None) -> int | None:
    today = today or date.today()
    for n in range(1, TOTAL_WEEKS + 1):
        s, e = week_range(n)
        if s <= today <= e:
            return n
    return None


def week_path(n: int) -> Path:
    s, e = week_range(n)
    return WEEK_DIR / f"W{n:02d} 任务单（{s:%Y-%m-%d}~{e:%m-%d}）.md"


# ---------------------------------------------------------------- 生成周任务单

def split_tasks(task_text: str) -> list:
    """把「装 Vivado / Verilator；注册一生一芯，读清单」拆成若干条"""
    out = []
    for major in SPLIT_MAJOR.split(task_text):
        for minor in SPLIT_MINOR.split(major):
            s = minor.strip().strip("*").strip()
            if s and len(s) > 1:
                out.append(s)
    return out


HOURS_RE = re.compile(r"^(?P<text>.*?)\s*(?P<h>\d+(?:\.\d+)?)\s*(?:h|H|小时)\s*$")
PAREN_LIST_RE = re.compile(r"^(?P<pre>.*?)[（(](?P<inner>[^（）()]*)[）)]\s*$")


def _expand_parenthetical(p: str) -> list:
    """「3 个 Verilog 小模块（计数器 / 状态机 / UART）」→ 三条，各自带上外层前缀"""
    m = PAREN_LIST_RE.match(p)
    if not m:
        return []
    inner = m.group("inner")
    parts = [s.strip() for s in re.split(r"[/、；;]", inner) if s.strip()]
    if len(parts) < 2:
        return []
    pre = m.group("pre").strip()
    # 「3 个 Verilog 小模块」→ 去掉数量，避免展开成「3 个…（计数器）」重复三次
    pre = re.sub(r"^\d+\s*个\s*", "", pre).strip()
    return [f"{pre}（{x}）" if pre else x for x in parts]


def split_tasks_with_hours(task_text: str, total_hours) -> list:
    """把一周的「主任务」拆成 (文本, 工时) 若干条，保证每条都带时间。

    规则：
      1. 文本里自带 `7h` / `7.5h` / `7小时` 的，用写明的数；
      2. 没写的，把剩下的工时平分（按 0.5h 取整，至少 0.5h）；
      3. 一条都没写，就把整周工时平分。
    """
    majors = [p.strip() for p in SPLIT_MAJOR.split(task_text or "") if p.strip()]
    if not majors:
        majors = ["未写主任务"]

    items = []                       # [文本, 工时 or None]
    for p in majors:
        m = HOURS_RE.match(p)
        if m and not SPLIT_MINOR.search(p):   # 整段自带工时且不可再分，直接用
            items.append([m.group("text").strip(), float(m.group("h"))])
            continue
        expanded = _expand_parenthetical(p)
        subs = expanded or [s.strip() for s in SPLIT_MINOR.split(p) if s.strip()] or [p]
        for s in subs:
            ms = HOURS_RE.match(s)
            if ms:
                items.append([ms.group("text").strip(), float(ms.group("h"))])
            else:
                items.append([s, None])

    total = float(total_hours or 0)
    known = sum(h for _, h in items if h)
    unknown = [i for i, (_, h) in enumerate(items) if not h]

    if unknown:
        share = max(total - known, 0.0) / len(unknown)
        for i in unknown:
            items[i][1] = max(0.5, round(share * 2) / 2)

    if sum(h for _, h in items) <= 0 and total > 0:
        share = total / len(items)
        for it in items:
            it[1] = max(0.5, round(share * 2) / 2)

    return [(t, float(h or 0)) for t, h in items]


def render_week(n: int, info: dict, existing_names: list) -> str:
    s, e = week_range(n)
    stage = info["stage"]
    hours = week_hours(n, stage)
    pairs = split_tasks_with_hours(info["task"], hours)
    ms = info["milestone"] if info["milestone"] not in ("", "—", "-") else "—"

    lines = [
        "---",
        f"week: {n}",
        f"range: {s} ~ {e}",
        f"stage: {stage}",
        f"hours_planned: {hours}",
        "---",
        "",
        f"# W{n:02d} 任务单（{s:%Y-%m-%d} ~ {e:%m-%d}）",
        "",
        "> [!info] 本周主线",
        f"> {info['task']}",
        f"> 阶段 **{STAGE_NAME.get(stage, stage)}** · 计划 **{hours}h**"
        + (f" · 硬节点：{ms}" if ms and ms not in ("—", "-") else ""),
        "",
        "## 任务",
        "",
    ]
    for i, (t, h) in enumerate(pairs, 1):
        lines.append(f"- [ ] W{n:02d}-{i:02d} {t} · {h:g}h")
    lines += [
        "",
        "## 记录",
        "",
        "| 项 | 计划 | 实际 |",
        "| --- | --- | --- |",
        f"| 工时 | {hours}h | |",
        "| 卡点 | — | |",
        "",
    ]
    return "\n".join(lines)


def cmd_week(args) -> int:
    tl = find_timeline()
    weeks = parse_weeks(read_text(tl))
    today = date.today()

    # 决定要「确保存在」哪几周
    if args.week:
        targets = [args.week]
    else:
        cur = current_week()
        if cur is not None:
            targets = [cur]
            # 周日晚上顺手把下周单也备好（周一开新周时不用再想起这件事）
            if today.weekday() == 6 and cur + 1 <= TOTAL_WEEKS:
                targets.append(cur + 1)
        elif W1_START - timedelta(days=7) <= today < W1_START:
            # 开跑前那一周：提前把 W1 备好
            targets = [1]
        else:
            s0, _ = week_range(1)
            print(f"[跳过] 今天不在 W1–W{TOTAL_WEEKS} 的日期范围内（W1 从 {s0} 开始）。")
            print("       要提前生成某周：python timeline.py week --week 1")
            return 0

    for target in targets:
        _ensure_week(weeks, target, args.dry)
    return 0


def _ensure_week(weeks: dict, n: int, dry: bool) -> None:
    if n not in weeks:
        print(f"[跳过] 逐周表里没有 W{n}")
        return
    p = week_path(n)
    if p.exists():
        print(f"[已存在] {p.name}（不覆盖）")
        return

    content = render_week(n, weeks[n], [])
    if dry:
        print(f"--- 将写入 {p.name} ---")
        print(content)
        return

    write_text(p, content)
    print(f"[生成] {p.name}")


# ---------------------------------------------------------------- 统计与回填

def scan_weeks() -> dict:
    """返回 {周号: {'total': n, 'done': n, 'file': Path}}"""
    result = {}
    if not WEEK_DIR.exists():
        return result
    for p in sorted(WEEK_DIR.glob("W*.md")):
        text = read_text(p)
        fm = frontmatter(text)
        try:
            n = int(fm.get("week", ""))
        except ValueError:
            m = re.match(r"W(\d+)", p.name)
            if not m:
                continue
            n = int(m.group(1))
        total = done = 0
        for line in text.splitlines():
            if TASK_LINE.match(line):
                total += 1
                if re.match(r"^- \[[xX]\] ", line):
                    done += 1
        result[n] = {"total": total, "done": done, "file": p}
    return result


def render_progress(weeks_info: dict, stats: dict) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    stage_acc = {}
    total_all = done_all = 0
    for n in sorted(stats):
        st = weeks_info.get(n, {}).get("stage", "?")
        t, d = stats[n]["total"], stats[n]["done"]
        total_all += t
        done_all += d
        a = stage_acc.setdefault(st, [0, 0, []])
        a[0] += t
        a[1] += d
        a[2].append(n)

    lines = [
        MARK_START,
        "## 八、实际进度（自动生成，勿手改）",
        "",
        f"> 由 `1-时间表/_tools/timeline.py` 于 {now} 生成。手改会在下次运行被覆盖。",
        "",
        "| 阶段 | 覆盖周 | 任务 | 已完成 | 完成率 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for st in sorted(stage_acc):
        t, d, ws = stage_acc[st]
        pct = f"{d / t * 100:.0f}%" if t else "—"
        wstr = f"W{min(ws)}–W{max(ws)}" if len(ws) > 1 else f"W{ws[0]}"
        lines.append(f"| {STAGE_NAME.get(st, st)} | {wstr} | {t} | {d} | {pct} |")
    pct_all = f"{done_all / total_all * 100:.0f}%" if total_all else "—"
    lines.append(f"| **合计** | — | **{total_all}** | **{done_all}** | **{pct_all}** |")
    lines.append("")

    n_now = current_week()
    if n_now and n_now in stats:
        t, d = stats[n_now]["total"], stats[n_now]["done"]
        pct = f"{d / t * 100:.0f}%" if t else "—"
        lines.append(f"本周 **W{n_now:02d}**：{d}/{t}（{pct}） · 累计 {done_all}/{total_all}（{pct_all}）")
    elif n_now:
        lines.append(f"本周 **W{n_now:02d}** 还没建任务单，双击 `同步时间表.cmd`。")
    else:
        lines.append(f"今天不在 W1–W{TOTAL_WEEKS} 范围内。")
    lines += ["", MARK_END]
    return "\n".join(lines)


def cmd_progress(args) -> int:
    tl = find_timeline()
    text = read_text(tl)
    weeks = parse_weeks(text)
    stats = scan_weeks()

    if not stats:
        print(f"[提示] {WEEK_DIR} 下还没有周任务单，跳过回填。")
        return 0

    block = render_progress(weeks, stats)

    if MARK_START in text and MARK_END in text:
        pre = text.split(MARK_START)[0]
        post = text.split(MARK_END, 1)[1]
        new = pre + block + post
    else:
        new = text.rstrip("\n") + "\n\n" + block + "\n"

    if new == text:
        print("[无变化] 时间表里的进度区块已是最新。")
        return 0

    if args.dry:
        print("--- 将写入的进度区块 ---")
        print(block)
        return 0

    backup(tl)
    write_text(tl, new)
    print(f"[回填] {tl.name}")

    n_now = current_week()
    if n_now and n_now in stats:
        t, d = stats[n_now]["total"], stats[n_now]["done"]
        pct = f"{d / t * 100:.0f}%" if t else "—"
        print(f"       本周 W{n_now:02d}：{d}/{t}（{pct}）")
    return 0


# ---------------------------------------------------------------- 入口

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="时间表任务同步工具")
    ap.add_argument("cmd", nargs="?", default="all", choices=["all", "week", "progress"])
    ap.add_argument("--week", type=int, help="指定周号（1–31），默认按今天算")
    ap.add_argument("--dry", action="store_true", help="只打印，不写盘")
    args = ap.parse_args(argv)

    if not TS_DIR.exists():
        die(f"找不到时间表目录：{TS_DIR}")

    rc = 0
    if args.cmd in ("all", "week"):
        rc = cmd_week(args) or rc
    if args.cmd in ("all", "progress"):
        rc = cmd_progress(args) or rc
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
