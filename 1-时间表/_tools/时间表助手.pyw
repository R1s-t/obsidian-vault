#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间表助手 —— 不依赖 Obsidian 的桌面小工具

双击本文件（.pyw）即可打开，不需要命令行、不需要开 Obsidian。

它做的事：
  · 左边列出全部 31 周，带完成率
  · 右边显示选中周的勾选清单，点一下就打勾（直接写回 1-时间表/周/*.md）
  · 底部显示本周进度条 + 累计进度
  · 可以新建某周任务单、回填时间表快照

数据仍然是同一份 Markdown —— 和 Obsidian 共用，不产生第二份真相。
"""

from __future__ import annotations

import os
import re
import sys
import traceback
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True          # 别在库目录里生成 __pycache__

import tkinter as tk
from tkinter import messagebox, ttk

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import timeline as TL  # noqa: E402

FONT = ("Microsoft YaHei UI", 10)
FONT_B = ("Microsoft YaHei UI", 10, "bold")
FONT_T = ("Microsoft YaHei UI", 16, "bold")
FONT_S = ("Microsoft YaHei UI", 9)

TASK_LINE_RE = re.compile(r"^(\s*)- \[( |x|X)\] (.+)$")
BOXED = re.compile(r"^(\s*)- \[( |x|X)\] (.*)$")

BG = "#faf9f7"
BG2 = "#ffffff"

EXAM_DATE = date(2027, 12, 25)      # 初试第一天
STOP_DATE = date(2027, 9, 6)        # 硬切换日：停项目转初试
WEEKDAY = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


# ------------------------------------------------------------------ 数据层

class WeekFile:
    """一周的任务单：读进来，改勾选，写回去。"""

    def __init__(self, n: int):
        self.n = n
        self.path = TL.week_path(n)
        self.exists = self.path.exists()
        self.lines: list[str] = []
        self.tasks: list[dict] = []      # 每个任务：{'line': 行号, 'id':..., 'text':..., 'done': bool}
        self.stage = ""
        self.date_range = ""
        self.hours = 0
        self.load()

    # -- 读
    def load(self) -> None:
        self.tasks = []
        self.lines = []
        if not self.exists:
            return
        text = TL.read_text(self.path)
        self.lines = text.split("\n")
        fm = TL.frontmatter(text)
        self.stage = fm.get("stage", "")
        self.date_range = fm.get("range", "")
        try:
            self.hours = int(fm.get("hours_planned", "0") or 0)
        except ValueError:
            self.hours = 0
        for i, line in enumerate(self.lines):
            m = TASK_LINE_RE.match(line)
            if not m:
                continue
            body = m.group(3).strip()
            tid = ""
            mm = re.match(r"^(W\d{2}-[A-Z]?\d+)\s*(.*)$", body)
            if mm:
                tid, body = mm.group(1), mm.group(2).strip()
            hrs = 0.0
            hm = re.search(r"[·•]\s*(\d+(?:\.\d+)?)\s*h\s*$", body)
            if hm:
                hrs = float(hm.group(1))
            self.tasks.append({
                "line": i,
                "id": tid,
                "text": body or "(未命名)",
                "done": m.group(2).lower() == "x",
                "hours": hrs,
            })

    # -- 统计
    @property
    def total(self) -> int:
        return len(self.tasks)

    @property
    def done(self) -> int:
        return sum(1 for t in self.tasks if t["done"])

    @property
    def hours_left(self) -> float:
        return round(sum(t.get("hours") or 0 for t in self.tasks if not t["done"]), 1)

    @property
    def hours_done(self) -> float:
        return round(sum(t.get("hours") or 0 for t in self.tasks if t["done"]), 1)

    # -- 改
    def set_done(self, idx: int, flag: bool) -> None:
        t = self.tasks[idx]
        if t["done"] == flag:
            return
        i = t["line"]
        old = self.lines[i]
        m = BOXED.match(old)
        if not m:
            return
        self.lines[i] = f"{m.group(1)}- [{'x' if flag else ' '}] {m.group(3)}"
        t["done"] = flag
        self.save()

    def save(self) -> None:
        TL.backup(self.path)
        TL.write_text(self.path, "\n".join(self.lines))

    # -- 建
    @staticmethod
    def create(n: int) -> tuple[bool, str]:
        tl = TL.find_timeline()
        weeks = TL.parse_weeks(TL.read_text(tl))
        if n not in weeks:
            return False, f"时间表的逐周表里没有 W{n}"
        p = TL.week_path(n)
        if p.exists():
            return False, "这一周的任务单已经存在了"
        TL.write_text(p, TL.render_week(n, weeks[n], []))
        return True, p.name


# ------------------------------------------------------------------ 界面层

class App:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.week: WeekFile | None = None
        self.current_n = TL.current_week()
        self._buildup_ui()
        self.refresh_weeks()
        self.select_week(self.current_n or 1)

    # ---------------- 构建界面
    def _buildup_ui(self) -> None:
        r = self.root
        r.title("时间表助手 · 2026-2028")
        r.geometry("1020x700")
        r.minsize(860, 560)
        r.configure(bg=BG)

        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("Treeview", font=FONT, rowheight=26)
        style.configure("Treeview.Heading", font=FONT_B)
        style.configure("TButton", font=FONT)
        style.configure("Big.TButton", font=FONT_B)
        style.configure("TPanedwindow", background=BG)

        # ---- 顶栏
        top = tk.Frame(r, bg=BG)
        top.pack(fill="x", padx=14, pady=(12, 6))
        tk.Label(top, text="时间表助手", font=FONT_T, bg=BG, fg="#222").pack(side="left")
        self.sub = tk.Label(top, text="", font=FONT_S, bg=BG, fg="#777")
        self.sub.pack(side="left", padx=12, pady=(6, 0))
        tk.Button(top, text="刷新", font=FONT, relief="flat", bg="#eceae6",
                  activebackground="#e0ded9", padx=12, cursor="hand2",
                  command=self.on_refresh).pack(side="right")
        tk.Button(top, text="回填", font=FONT, relief="flat", bg="#eceae6",
                  activebackground="#e0ded9", padx=12, cursor="hand2",
                  command=self.on_snapshot).pack(side="right", padx=6)
        tk.Button(top, text="周文件夹", font=FONT, relief="flat", bg="#eceae6",
                  activebackground="#e0ded9", padx=12, cursor="hand2",
                  command=self.open_folder).pack(side="right")
        tk.Button(top, text="本周文件", font=FONT, relief="flat", bg="#eceae6",
                  activebackground="#e0ded9", padx=12, cursor="hand2",
                  command=self.open_week_file).pack(side="right", padx=6)
        tk.Button(top, text="生成下一周", font=FONT, relief="flat", bg="#dcebdc",
                  activebackground="#cbe0cb", padx=12, cursor="hand2",
                  command=self.on_next_week).pack(side="right", padx=(0, 6))

        # ---- 主体：左列表 + 右详情
        body = tk.Frame(r, bg=BG)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        left = tk.Frame(body, bg=BG, width=300)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        tk.Label(left, text="全部 31 周", font=FONT_B, bg=BG, fg="#555",
                 anchor="w").pack(fill="x", pady=(0, 6))

        cols = ("w", "d", "p")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=20)
        self.tree.heading("w", text="周")
        self.tree.heading("d", text="日期")
        self.tree.heading("p", text="完成")
        self.tree.column("w", width=52, anchor="w")
        self.tree.column("d", width=118, anchor="w")
        self.tree.column("p", width=72, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.tag_configure("cur", background="#fff4d6")
        self.tree.tag_configure("none", foreground="#b0b0b0")
        # 防重入：select_week 内部会 selection_set，若不加闸会与 on_pick 互相触发
        self._suppress_pick = False
        self.tree.bind("<<TreeviewSelect>>", self.on_pick)

        self.l_sum = tk.Label(left, text="", font=FONT_S, bg=BG, fg="#888", anchor="w")
        self.l_sum.pack(fill="x", pady=(6, 0))

        # ---- 右侧
        right = tk.Frame(body, bg=BG2, highlightthickness=1,
                         highlightbackground="#e4e1db")
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        head = tk.Frame(right, bg=BG2)
        head.pack(fill="x", padx=18, pady=(14, 4))
        self.h_title = tk.Label(head, text="", font=("Microsoft YaHei UI", 15, "bold"),
                                bg=BG2, fg="#1a1a1a", anchor="w")
        self.h_title.pack(fill="x")
        self.h_meta = tk.Label(head, text="", font=FONT_S, bg=BG2, fg="#777", anchor="w")
        self.h_meta.pack(fill="x", pady=(2, 0))
        self.h_badge = tk.Label(head, text="", font=FONT_S, bg="#fdf1e0", fg="#a06000",
                                anchor="w", padx=8, pady=2)
        self.h_main = tk.Label(head, text="", font=FONT, bg=BG2, fg="#444",
                               anchor="w", justify="left", wraplength=600)
        self.h_main.pack(fill="x", pady=(6, 0))

        # 可滚动任务区
        wrap = tk.Frame(right, bg=BG2)
        wrap.pack(fill="both", expand=True, padx=18, pady=(10, 4))
        self.canvas = tk.Canvas(wrap, bg=BG2, highlightthickness=0)
        sb = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=BG2)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind_all(seq, self._on_wheel, add="+")

        # 底部进度
        foot = tk.Frame(right, bg=BG2)
        foot.pack(fill="x", padx=18, pady=(4, 14))
        self.bar = ttk.Progressbar(foot, mode="determinate", maximum=100)
        self.bar.pack(fill="x")
        row = tk.Frame(foot, bg=BG2)
        row.pack(fill="x", pady=(6, 0))
        self.p_week = tk.Label(row, text="", font=FONT_B, bg=BG2, fg="#1f6f3f", anchor="w")
        self.p_week.pack(side="left")
        self.p_all = tk.Label(row, text="", font=FONT_S, bg=BG2, fg="#777", anchor="e")
        self.p_all.pack(side="right")
        self.btn_new = tk.Button(foot, text="为这一周生成任务单", font=FONT_B,
                                 relief="flat", bg="#1f6f3f", fg="white",
                                 activebackground="#175432", activeforeground="white",
                                 padx=18, pady=6, cursor="hand2",
                                 command=self.on_create)
        self.btn_new.pack(pady=(10, 0))

        r.bind("<Control-r>", lambda e: self.on_refresh())
        r.bind("<Escape>", lambda e: r.destroy())
        r.bind("<Left>", lambda e: self.step(-1))
        r.bind("<Right>", lambda e: self.step(1))

    # ---------------- 滚动
    def _on_wheel(self, e):
        if not self.canvas.winfo_containing(e.x_root, e.y_root):
            return
        if getattr(e, "num", None) == 4:
            self.canvas.yview_scroll(-3, "units")
        elif getattr(e, "num", None) == 5:
            self.canvas.yview_scroll(3, "units")
        else:
            self.canvas.yview_scroll(int(-1 * (e.delta / 120)) * 3, "units")

    # ---------------- 左侧列表
    def refresh_weeks(self) -> None:
        stats = TL.scan_weeks()
        try:
            weeks = TL.parse_weeks(TL.read_text(TL.find_timeline()))
        except SystemExit:
            messagebox.showerror("找不到时间表", "在 1-时间表/ 下没有找到 *全周期时间表*.md")
            self.root.destroy()
            return
        self.weeks = weeks
        self.tree.delete(*self.tree.get_children())
        for n in range(1, TL.TOTAL_WEEKS + 1):
            info = weeks.get(n, {})
            rng = info.get("date", "")
            if n in stats:
                t, d = stats[n]["total"], stats[n]["done"]
                pct = f"{d}/{t}  {d / t * 100:.0f}%" if t else "0/0"
                tags = ("cur",) if n == self.current_n else ()
            else:
                pct = "未建"
                tags = ("none",)
            self.tree.insert("", "end", iid=str(n),
                             values=(f"W{n:02d}", rng, pct), tags=tags)
        if self.current_n:
            self.tree.see(str(self.current_n))
        tc = date.today()
        d_stop = (STOP_DATE - tc).days
        d_exam = (EXAM_DATE - tc).days
        cd = (f"距停项目 {d_stop} 天　·　距初试 {d_exam} 天" if d_stop > 0
              else f"距初试 {d_exam} 天")
        cur = f"当前 W{self.current_n:02d}" if self.current_n else "不在计划周内"
        self.sub.config(text=f"今天 {tc:%Y-%m-%d} {WEEKDAY[tc.weekday()]}　·　{cur}　·　{cd}")

        built = len(stats)
        tot = sum(s["total"] for s in stats.values())
        dn = sum(s["done"] for s in stats.values())
        self.l_sum.config(text=f"已建 {built}/{TL.TOTAL_WEEKS} 周　·　{tot} 项　·　完成 {dn}")

    # ---------------- 选中某周
    def on_pick(self, _evt=None) -> None:
        if self._suppress_pick:
            return
        sel = self.tree.selection()
        if not sel:
            return
        n = int(sel[0])
        # 只有「选中的周确实换了」才重渲染；同一周重复点不做任何事。
        # 注意不能加 `and self.week.exists`——未建的周会因此一路递归到卡死。
        if self.week and self.week.n == n:
            return
        self.select_week(n)

    def select_week(self, n: int) -> None:
        self.week = WeekFile(n)
        if self.tree.exists(str(n)):
            self._suppress_pick = True
            self.tree.selection_set(str(n))
            self.tree.focus(str(n))
            self.root.after_idle(self._release_pick)
        self.render()

    def _release_pick(self) -> None:
        self._suppress_pick = False

    # ---------------- 右侧渲染
    def clear_inner(self) -> None:
        for w in self.inner.winfo_children():
            w.destroy()

    def render(self) -> None:
        self.clear_inner()
        w = self.week
        assert w is not None
        s, e = TL.week_range(w.n)
        info = self.weeks.get(w.n) or {}
        tbl_stage = info.get("stage", "")
        stage_raw = w.stage or tbl_stage          # 周单还没建时，退回逐周表里的阶段
        stage = TL.STAGE_NAME.get(stage_raw, stage_raw or "—")

        self.h_title.config(text=f"W{w.n:02d}　{s:%Y-%m-%d} ~ {e:%m-%d}")
        plan = w.hours or TL.week_hours(w.n, stage_raw)
        today = date.today()
        if s <= today <= e:
            day_txt = f"本周第 {(today - s).days + 1}/7 天"
        elif today < s:
            day_txt = f"还有 {(s - today).days} 天开始"
        else:
            day_txt = "已过去"
        cnt = f"{len(w.tasks)} 项" if w.exists else "周单未建"
        self.h_meta.config(text=f"{stage}　·　计划 {plan}h　·　{cnt}　·　{day_txt}")

        ms = info.get("milestone", "")
        if ms and ms not in ("", "—", "-"):
            self.h_badge.config(text=f"⏰ 硬节点：{ms}")
            self.h_badge.pack(fill="x", pady=(6, 0), before=self.h_main)
        else:
            self.h_badge.config(text="")
            self.h_badge.pack_forget()

        if not w.exists:
            self.h_main.config(text="这一周的任务单还没生成。")
            self.btn_new.pack(pady=(10, 0))
            tk.Label(self.inner, text="点下面的按钮生成这一周的任务单。",
                     font=FONT, bg=BG2, fg="#888").pack(anchor="w", pady=20)
            self.bar.config(value=0)
            self.p_week.config(text="—")
            self.p_all.config(text="")
            return

        self.btn_new.pack_forget()
        main = self.weeks.get(w.n, {}).get("task", "")
        self.h_main.config(text=main)

        # 任务清单：一列到底，不分组
        for idx, t in enumerate(w.tasks):
            var = tk.BooleanVar(value=t["done"])
            cb = tk.Checkbutton(
                self.inner, text=t["text"], variable=var, font=FONT,
                bg=BG2, activebackground=BG2, anchor="w", justify="left",
                wraplength=560, padx=6, pady=4, cursor="hand2",
                fg="#999" if t["done"] else "#222",
                command=lambda i=idx, v=var: self.on_toggle(i, v),
            )
            cb.pack(fill="x", anchor="w")
            if t["done"]:
                cb.configure(font=(FONT[0], FONT[1], "overstrike"))

        self.update_progress()

    def update_progress(self) -> None:
        w = self.week
        assert w is not None
        t, d = w.total, w.done
        pct = (d / t * 100) if t else 0
        self.bar.config(value=pct)
        self.p_week.config(text=f"本周 {d}/{t}　{pct:.0f}%　·　剩 {t - d} 项 ≈{w.hours_left:g}h")
        all_t = all_d = 0
        for n, st in TL.scan_weeks().items():
            all_t += st["total"]
            all_d += st["done"]
        if all_t:
            self.p_all.config(text=f"累计 {all_d}/{all_t}（{all_d / all_t * 100:.0f}%）")

    # ---------------- 交互
    def on_toggle(self, idx: int, var: tk.BooleanVar) -> None:
        w = self.week
        assert w is not None
        try:
            w.set_done(idx, bool(var.get()))
        except Exception:
            messagebox.showerror("写回失败", traceback.format_exc(limit=2))
            return
        self.render()
        self.refresh_row(w.n)

    def refresh_row(self, n: int) -> None:
        w = self.week
        if not w or w.n != n or not self.tree.exists(str(n)):
            return
        t, d = w.total, w.done
        pct = f"{d}/{t}  {d / t * 100:.0f}%" if t else "0/0"
        s, e = TL.week_range(n)
        self.tree.item(str(n), values=(f"W{n:02d}", self.weeks.get(n, {}).get("date", ""), pct))

    def on_next_week(self) -> None:
        """在「当前选中的周」之后建下一周；没选中就用今天所在周。"""
        base = self.week.n if self.week else (self.current_n or 1)
        n = base + 1
        if n > TL.TOTAL_WEEKS:
            messagebox.showinfo("到头了", f"一共 {TL.TOTAL_WEEKS} 周，W{n} 超出范围。")
            return
        if TL.week_path(n).exists():
            self.select_week(n)
            messagebox.showinfo("已存在", f"W{n:02d} 的任务单已经有了，已跳过去。")
            return
        ok, msg = WeekFile.create(n)
        if ok:
            self.refresh_weeks()
            self.select_week(n)
            messagebox.showinfo("已生成", f"{msg}")
        else:
            messagebox.showwarning("没生成", msg)

    def on_create(self) -> None:
        if not self.week:
            return
        n = self.week.n
        ok, msg = WeekFile.create(n)
        if ok:
            self.refresh_weeks()
            self.select_week(n)
            messagebox.showinfo("已生成", f"{msg}")
        else:
            messagebox.showwarning("没生成", msg)

    def on_snapshot(self) -> None:
        class A:
            dry = False
        try:
            TL.cmd_progress(A())
        except SystemExit:
            pass
        except Exception:
            messagebox.showerror("回填失败", traceback.format_exc(limit=3))
            return
        messagebox.showinfo("已回填", "时间表的「八、实际进度」已刷新。")

    def on_refresh(self) -> None:
        n = self.week.n if self.week else 1
        self.current_n = TL.current_week()
        self.refresh_weeks()
        self.select_week(n)

    def step(self, delta: int) -> None:
        base = self.week.n if self.week else 1
        n = min(max(base + delta, 1), TL.TOTAL_WEEKS)
        if n != base:
            self.select_week(n)

    def open_week_file(self) -> None:
        w = self.week
        if not w:
            return
        if not w.exists:
            messagebox.showinfo("还没有", "这一周的任务单还没生成。")
            return
        try:
            os.startfile(str(w.path))  # type: ignore[attr-defined]
        except Exception:
            messagebox.showinfo("路径", str(w.path))

    def open_folder(self) -> None:
        try:
            os.startfile(TL.WEEK_DIR)  # type: ignore[attr-defined]
        except Exception:
            messagebox.showinfo("路径", str(TL.WEEK_DIR))


def main() -> None:
    root = tk.Tk()
    try:
        app = App(root)
    except Exception:
        messagebox.showerror("启动失败", traceback.format_exc())
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
