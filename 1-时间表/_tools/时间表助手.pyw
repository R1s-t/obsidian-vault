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
FONT_T = ("Microsoft YaHei UI", 18)          # 大标题：大 + 细字重，不用 bold
FONT_H = ("Microsoft YaHei UI", 15)          # 右侧周标题
FONT_NUM = ("Microsoft YaHei UI", 17, "bold")  # 统计数字
FONT_S = ("Microsoft YaHei UI", 9)
FONT_XS = ("Microsoft YaHei UI", 9)

TASK_LINE_RE = re.compile(r"^(\s*)- \[( |x|X)\] (.+)$")
BOXED = re.compile(r"^(\s*)- \[( |x|X)\] (.*)$")

# ---- 配色：苹果极简白的中性色阶 + 一个深绿主色（只用于进度与主按钮）
BG = "#f5f5f7"          # 窗口底（canvas-alt）
BG2 = "#ffffff"         # 卡片底
LINE = "#d2d2d7"        # hairline
INK = "#1d1d1f"         # 主文字（近黑）
INK2 = "#6e6e73"        # 次要文字
INK3 = "#86868b"        # 更弱
ACCENT = "#2f6b4f"      # 主色（深绿）
ACCENT_D = "#23543d"    # 主色按下
ACCENT_BG = "#e8f5ee"   # 主色浅底（bento 浅绿）
WARN_BG = "#fdf0ef"     # 硬节点底（bento 浅橙）
WARN_FG = "#a04a2a"     # 硬节点字
CUR_BG = "#fff7e6"      # 当前周高亮（bento 浅黄）
TILE_BLUE = "#eef2ff"   # 阶段统计卡底（bento 浅蓝）
HOVER = "#fafafa"       # 白底上的 hover

EXAM_DATE = date(2027, 12, 18)      # 初试第一天
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
            self.hours = float(fm.get("hours_planned", "0") or 0)
        except ValueError:
            self.hours = 0.0
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
        r.geometry("1100x650")
        r.minsize(860, 560)
        r.configure(bg=BG)

        style = ttk.Style()
        style.theme_use("clam")          # vista 主题改不动 Treeview 底色，clam 可以
        style.configure("Treeview", font=FONT, rowheight=31,
                        background=BG2, fieldbackground=BG2,
                        borderwidth=0, relief="flat")
        style.map("Treeview",
                  background=[("selected", ACCENT_BG)],
                  foreground=[("selected", INK)])
        style.configure("Treeview.Heading", font=FONT_S, background=BG2,
                        foreground=INK3, relief="flat", borderwidth=0, padding=(8, 8))
        style.map("Treeview.Heading", background=[("active", BG2)])
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.configure("Green.Horizontal.TProgressbar", troughcolor="#ececf0",
                        background=ACCENT, thickness=8, borderwidth=0,
                        lightcolor=ACCENT, darkcolor=ACCENT)
        style.configure("TScrollbar", troughcolor=BG2, background=LINE,
                        borderwidth=0, arrowsize=12, relief="flat")
        style.map("TScrollbar", background=[("active", "#c7c7cc")])

        # ---- 顶栏（第一行只放标题和按钮，副标题单独一行——不然窄屏下按钮会被挤没）
        top = tk.Frame(r, bg=BG)
        top.pack(fill="x", padx=20, pady=(16, 0))

        line1 = tk.Frame(top, bg=BG)
        line1.pack(fill="x")

        # 按钮先占位（pack 先来先得），标题再吃剩下的
        bar = tk.Frame(line1, bg=BG)
        bar.pack(side="right")
        self.btn_sync = self._mkbtn(bar, "同步", self.on_sync, primary=True)
        self.btn_sync.pack(side="right")
        self.btn_dir = self._mkbtn(bar, "周文件夹", self.open_folder)
        self.btn_dir.pack(side="right", padx=(0, 6))
        self.btn_this = self._mkbtn(bar, "本周文件", self.open_week_file)
        self.btn_this.pack(side="right", padx=(0, 6))
        self.status = tk.Label(bar, text="", font=FONT_XS, bg=BG, fg=ACCENT)
        self.status.pack(side="right", padx=(0, 12))

        tk.Label(line1, text="时间表助手", font=FONT_T, bg=BG, fg=INK).pack(side="left")

        self.sub = tk.Label(top, text="", font=FONT_XS, bg=BG, fg=INK3, anchor="w")
        self.sub.pack(fill="x", pady=(6, 0))

        # 顶栏下的分隔线
        tk.Frame(r, bg=LINE, height=1).pack(fill="x", padx=20, pady=(14, 0))

        # ---- 主体：左列表 + 右详情
        body = tk.Frame(r, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=(14, 16))

        left = tk.Frame(body, bg=BG, width=316)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        lhead = tk.Frame(left, bg=BG)
        lhead.pack(fill="x", pady=(0, 8))
        tk.Label(lhead, text="全部 31 周", font=FONT_B, bg=BG, fg=INK2,
                 anchor="w").pack(side="left")
        self.l_sum = tk.Label(lhead, text="", font=FONT_XS, bg=BG, fg=INK3, anchor="e")
        self.l_sum.pack(side="right")

        # 左栏底部：本阶段节奏（时间过了多少 vs 任务做了多少）+ 下一个硬节点
        pacebox = tk.Frame(left, bg=BG)
        pacebox.pack(side="bottom", fill="x", pady=(10, 0))
        self.pace: dict[str, tuple[tk.Frame, tk.Label]] = {}
        for key, label, color in (("time", "时间", INK3), ("task", "任务", ACCENT)):
            row = tk.Frame(pacebox, bg=BG)
            row.pack(fill="x", pady=(0, 5))
            tk.Label(row, text=label, font=FONT_XS, bg=BG, fg=INK3, width=4,
                     anchor="w").pack(side="left")
            pct = tk.Label(row, text="—", font=FONT_XS, bg=BG, fg=INK2, width=5, anchor="e")
            pct.pack(side="right")
            track = tk.Frame(row, bg="#ececf0", height=5)
            track.pack(side="left", fill="x", expand=True, padx=(6, 8))
            track.pack_propagate(False)
            fill = tk.Frame(track, bg=color, height=5)
            fill.place(x=0, y=0, relheight=1, relwidth=0)
            self.pace[key] = (fill, pct)
        self.h_next = tk.Label(pacebox, text="", font=FONT_XS, bg=BG, fg=INK2,
                               anchor="w", justify="left", wraplength=292)
        self.h_next.pack(fill="x", pady=(3, 0))

        lcard = tk.Frame(left, bg=BG2)
        lcard.pack(fill="both", expand=True)

        cols = ("w", "d", "p")
        lwrap = tk.Frame(lcard, bg=BG2)
        lwrap.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(lwrap, columns=cols, show="headings", height=18)
        self.tsb = ttk.Scrollbar(lwrap, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tsb.set)
        self.tree.heading("w", text="周")
        self.tree.heading("d", text="日期")
        self.tree.heading("p", text="完成")
        self.tree.column("w", width=56, anchor="w")
        self.tree.column("d", width=130, anchor="w")
        self.tree.column("p", width=84, anchor="center")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tsb.pack(side="right", fill="y")
        self.tree.tag_configure("cur", background=CUR_BG, foreground=INK)
        self.tree.tag_configure("none", foreground=INK3)
        self.tree.tag_configure("done", foreground=ACCENT)
        # 左侧列表的滚轮：31 行在小窗口装不下，得能滚
        self.tree.bind("<MouseWheel>", self._on_tree_wheel)
        self.tree.bind("<Button-4>", lambda e: self.tree.yview_scroll(-3, "units"))
        self.tree.bind("<Button-5>", lambda e: self.tree.yview_scroll(3, "units"))
        # 防重入：select_week 内部会 selection_set，若不加闸会与 on_pick 互相触发
        self._suppress_pick = False
        self.tree.bind("<<TreeviewSelect>>", self.on_pick)

        # ---- 右侧
        right = tk.Frame(body, bg=BG2)
        right.pack(side="left", fill="both", expand=True, padx=(14, 0))

        head = tk.Frame(right, bg=BG2)
        head.pack(fill="x", padx=24, pady=(20, 0))

        titlerow = tk.Frame(head, bg=BG2)
        titlerow.pack(fill="x")
        # 标题左侧的竖线，充当视觉锚点
        tk.Frame(titlerow, bg=ACCENT, width=3, height=20).pack(side="left", padx=(0, 10))
        self.h_title = tk.Label(titlerow, text="", font=FONT_H,
                                bg=BG2, fg=INK, anchor="w")
        self.h_title.pack(side="left")

        self.h_meta = tk.Label(head, text="", font=FONT_XS, bg=BG2, fg=INK3, anchor="w")
        self.h_meta.pack(fill="x", pady=(7, 0))

        # 三个指标卡（本周 / 阶段 / 全部）：数字大、标签小，一眼看出差多少
        self.cards: dict[str, tuple[tk.Label, tk.Label]] = {}
        cardrow = tk.Frame(head, bg=BG2)
        cardrow.pack(fill="x", pady=(12, 0))
        specs = (("week", "本周", ACCENT_BG),
                 ("phase", "本阶段", TILE_BLUE),
                 ("all", "全部", BG))
        for i, (key, label, tint) in enumerate(specs):
            card = tk.Frame(cardrow, bg=tint)
            card.pack(side="left", fill="x", expand=True,
                      padx=(0, 8) if i < len(specs) - 1 else 0)
            num = tk.Label(card, text="—", font=FONT_NUM, bg=tint, fg=INK, anchor="w")
            num.pack(fill="x", padx=14, pady=(9, 0))
            tag = tk.Label(card, text=label, font=FONT_XS, bg=tint, fg=INK3, anchor="w")
            tag.pack(fill="x", padx=14, pady=(1, 9))
            self.cards[key] = (num, tag)

        self.h_badge = tk.Label(head, text="", font=FONT_XS, bg=WARN_BG, fg=WARN_FG,
                                anchor="w", padx=10, pady=3)
        self.h_main = tk.Label(head, text="", font=FONT, bg=BG2, fg=INK2,
                               anchor="w", justify="left", wraplength=620)
        self.h_main.pack(fill="x", pady=(8, 0))

        tk.Frame(right, bg=LINE, height=1).pack(fill="x", padx=24, pady=(16, 0))

        # 可滚动任务区
        wrap = tk.Frame(right, bg=BG2)
        wrap.pack(fill="both", expand=True, padx=24, pady=(6, 4))
        self.canvas = tk.Canvas(wrap, bg=BG2, highlightthickness=0)
        self.sb = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.sb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=BG2)
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self._sync_scroll())
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind_all(seq, self._on_wheel, add="+")
        self._scroll_need = False

        # 底部进度（累计数字在上面的指标卡里，这里只留本周一行）
        # 注意先把它插到 wrap 前面占位，否则 expand 的任务区会把它挤出窗口
        foot = tk.Frame(right, bg=BG2)
        foot.pack(side="bottom", fill="x", padx=24, pady=(6, 14), before=wrap)
        self.bar = ttk.Progressbar(foot, mode="determinate", maximum=100,
                                   style="Green.Horizontal.TProgressbar")
        self.bar.pack(fill="x")
        row = tk.Frame(foot, bg=BG2)
        row.pack(fill="x", pady=(8, 0))
        self.p_week = tk.Label(row, text="", font=FONT_XS, bg=BG2, fg=INK2, anchor="w")
        self.p_week.pack(side="left")
        self.btn_new = self._mkbtn(foot, "为这一周生成任务单", self.on_create, primary=True)
        self.btn_new.pack(pady=(12, 0))

        r.bind("<Control-r>", lambda e: self.on_sync())
        r.bind("<Escape>", lambda e: self._on_quit())
        r.protocol("WM_DELETE_WINDOW", self._on_quit)
        r.bind("<Left>", lambda e: self.step(-1))
        r.bind("<Right>", lambda e: self.step(1))

    def _mkbtn(self, parent, text, cmd, primary=False):
        """统一样式的扁平按钮：primary 深绿实底，其余白底描边，都带 hover。"""
        b = tk.Button(parent, text=text,
                      font=FONT_B if primary else FONT,
                      relief="flat", bd=0, cursor="hand2",
                      padx=16, pady=6 if primary else 5,
                      bg=ACCENT if primary else BG2,
                      fg="white" if primary else INK2,
                      activebackground=ACCENT_D if primary else HOVER,
                      activeforeground="white" if primary else INK,
                      highlightthickness=0 if primary else 1,
                      highlightbackground=LINE, highlightcolor=LINE,
                      command=cmd)
        if not primary:
            b.bind("<Enter>", lambda e: b.config(bg=HOVER))
            b.bind("<Leave>", lambda e: b.config(bg=BG2))
        return b

    def _flash(self, msg: str, ms: int = 2600) -> None:
        """在顶栏右侧短暂显示一句提示，替代弹窗。"""
        self.status.config(text=msg)
        if getattr(self, "_flash_job", None):
            try:
                self.root.after_cancel(self._flash_job)
            except Exception:
                pass
        self._flash_job = self.root.after(ms, lambda: self.status.config(text=""))

    # ---------------- 滚动
    def _on_canvas_resize(self, e) -> None:
        self.canvas.itemconfigure(self._win, width=e.width)
        self._sync_scroll()

    def _sync_scroll(self) -> None:
        """内容比可视区高才显示滚动条；否则隐藏并把视图钉回顶部。"""
        if not self.canvas.winfo_exists():
            return
        need = self.inner.winfo_reqheight()
        have = self.canvas.winfo_height()
        taller = need > have
        if taller != self._scroll_need:
            self._scroll_need = taller
            if taller:
                self.sb.pack(side="right", fill="y")
            else:
                self.sb.pack_forget()
                self.canvas.yview_moveto(0)
        self.canvas.configure(
            scrollregion=(0, 0, self.canvas.winfo_width(), need if taller else have))
        # 任务文字的换行宽度跟着窗口走（留出勾选框与滚动条的余量）
        wrap = max(260, self.canvas.winfo_width() - (116 if taller else 96))
        for child in self.inner.winfo_children():
            if isinstance(child, tk.Checkbutton) and int(child.cget("wraplength")) != wrap:
                child.configure(wraplength=wrap)
        # 上周主线那段说明也跟着走
        hm = max(320, self.canvas.winfo_width() - 8)
        if int(self.h_main.cget("wraplength")) != hm:
            self.h_main.configure(wraplength=hm)

    def _on_tree_wheel(self, e) -> None:
        step = -3 if e.delta > 0 else 3
        self.tree.yview_scroll(step, "units")

    def _on_wheel(self, e) -> None:
        if not self._scroll_need:
            return
        x, y = self.canvas.winfo_pointerxy()
        cx, cy = self.canvas.winfo_rootx(), self.canvas.winfo_rooty()
        if not (cx <= x < cx + self.canvas.winfo_width()
                and cy <= y < cy + self.canvas.winfo_height()):
            return
        if getattr(e, "num", None) in (4, 5):
            step = -3 if e.num == 4 else 3
        else:
            step = -3 if e.delta > 0 else 3
        self.canvas.yview_scroll(step, "units")

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
            # 列表还没布局完时 see() 会算错，等一拍再定位
            self.root.after_idle(lambda n=self.current_n: self.tree.see(str(n)))
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
            self.tree.see(str(n))
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
        self.h_meta.config(text=f"{stage}　·　计划 {plan:g}h　·　{cnt}　·　{day_txt}")

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
                     font=FONT, bg=BG2, fg=INK3).pack(anchor="w", pady=20)
            self.bar.config(value=0)
            self.p_week.config(text="—")
            self._update_cards()
            self.root.after_idle(self._sync_scroll)
            return

        self.btn_new.pack_forget()
        main = self.weeks.get(w.n, {}).get("task", "")
        # 逐周表里的 Markdown 粗体标记在 Label 里不解析，露出来很丑，去掉
        self.h_main.config(text=main.replace("**", ""))

        # 任务清单：一列到底，不分组
        wl = max(280, self.canvas.winfo_width() - 96)
        for idx, t in enumerate(w.tasks):
            var = tk.BooleanVar(value=t["done"])
            cb = tk.Checkbutton(
                self.inner, text=t["text"].replace("**", ""), variable=var,
                font=FONT if not t["done"] else (FONT[0], FONT[1], "overstrike"),
                bg=BG2, activebackground=ACCENT_BG, selectcolor=BG2,
                anchor="w", justify="left", wraplength=wl,
                padx=2, pady=6, bd=0, highlightthickness=0, cursor="hand2",
                fg=INK3 if t["done"] else INK,
                activeforeground=INK,
                command=lambda i=idx, v=var: self.on_toggle(i, v),
            )
            cb.pack(fill="x", anchor="w")
            # hover：整行浅底，指哪读哪
            cb.bind("<Enter>", lambda e, c=cb: c.config(bg=HOVER))
            cb.bind("<Leave>", lambda e, c=cb: c.config(bg=BG2))

        self.update_progress()
        self.root.after_idle(self._sync_scroll)

    def update_progress(self) -> None:
        w = self.week
        assert w is not None
        t, d = w.total, w.done
        pct = (d / t * 100) if t else 0
        self.bar.config(value=pct)
        self.p_week.config(text=f"本周 {d}/{t}　{pct:.0f}%　·　剩 {t - d} 项 ≈{w.hours_left:g}h")
        self._update_cards()

    # ---------------- 指标卡
    def _phase_counts(self, stage: str) -> tuple[int, int]:
        """某个阶段（P0/P1…）下所有已建周的 完成数 / 总数。"""
        if not stage:
            return 0, 0
        stats = TL.scan_weeks()
        done = tot = 0
        for n, info in self.weeks.items():
            if info.get("stage", "") != stage:
                continue
            st = stats.get(n)
            if not st:
                continue
            done += st["done"]
            tot += st["total"]
        return done, tot

    def _put_card(self, key: str, label: str, d: int, t: int) -> None:
        num, tag = self.cards[key]
        if t:
            num.config(text=f"{d}/{t}")
            tag.config(text=f"{label} · {d / t * 100:.0f}%")
        else:
            num.config(text="—")
            tag.config(text=label)

    def _phase_span(self, stage: str):
        """某个阶段覆盖的起止日期（取该阶段所有周的并集）。"""
        if not stage:
            return None
        ns = [n for n, info in self.weeks.items() if info.get("stage") == stage]
        if not ns:
            return None
        s0, _ = TL.week_range(min(ns))
        _, e1 = TL.week_range(max(ns))
        return s0, e1

    def _set_pace(self, key: str, pct: float) -> None:
        if key not in getattr(self, "pace", {}):
            return
        fill, lab = self.pace[key]
        fill.place_configure(relwidth=max(0.0, min(1.0, pct / 100.0)))
        lab.config(text=f"{pct:.0f}%")

    def _next_milestone(self, from_n: int):
        """从第 from_n 周往后找最近的硬节点。"""
        for n in range(max(1, from_n), TL.TOTAL_WEEKS + 1):
            ms = self.weeks.get(n, {}).get("milestone", "")
            if ms and ms not in ("", "—", "-"):
                s, _ = TL.week_range(n)
                return n, ms, s
        return None

    def _update_cards(self) -> None:
        w = self.week
        if not w:
            return
        info = self.weeks.get(w.n) or {}
        stage_raw = w.stage or info.get("stage", "")
        stats = TL.scan_weeks()
        all_t = sum(s["total"] for s in stats.values())
        all_d = sum(s["done"] for s in stats.values())
        ph_d, ph_t = self._phase_counts(stage_raw)
        self._put_card("week", "本周", w.done, w.total)
        self._put_card("phase", stage_raw or "本阶段", ph_d, ph_t)
        self._put_card("all", "全部", all_d, all_t)

        # 节奏条：时间过了多少 vs 任务做了多少
        span = self._phase_span(stage_raw)
        if span:
            s0, e1 = span
            total = max(1, (e1 - s0).days)
            passed = max(0, min(total, (date.today() - s0).days))
            t_pct = passed / total * 100
        else:
            t_pct = 0.0
        self._set_pace("time", t_pct)
        self._set_pace("task", (ph_d / ph_t * 100) if ph_t else 0.0)

        # 下一个硬节点
        node = getattr(self, "h_next", None)
        if node is None:
            return
        nm = self._next_milestone(w.n)
        if nm:
            n, ms, s = nm
            days = (s - date.today()).days
            when = f"还有 {days} 天" if days > 0 else "已到"
            node.config(text=f"下一个硬节点：W{n:02d} · {ms} · {when}")
        else:
            node.config(text="")

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

    def _on_quit(self) -> None:
        self.root.destroy()

    def on_sync(self) -> None:
        """一次做完两件事：把勾选进度写回时间表页，再重读界面。"""
        n = self.week.n if self.week else 1
        try:
            class A:
                dry = False
            TL.cmd_progress(A())
        except SystemExit:
            self._flash("时间表没找到，回填跳过")
        except Exception:
            messagebox.showerror("回填失败", traceback.format_exc(limit=3))
            return
        self.current_n = TL.current_week()
        self.refresh_weeks()
        self.select_week(n)
        self._flash("已同步 · 时间表「八、实际进度」已更新")
        self._flash("已同步 · 时间表「八、实际进度」已更新")

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


def _ascii_icon(src: Path) -> Path | None:
    """把图标复制到纯 ASCII 的临时路径再返回。

    Tk 在 Windows 上用 ANSI 接口读 .ico，中文路径会「调用成功但图标不生效」，
    而且不报错——实测标题栏一直是 Tk 默认的羽毛。绕开的办法是先复制一份到
    %TEMP%（路径里只有 ASCII），再从那里加载。
    """
    if not src.exists():
        return None
    try:
        src.name.encode("ascii")
        if str(src).isascii():
            return src
    except UnicodeEncodeError:
        pass
    try:
        import shutil
        dst = Path(os.environ.get("TEMP") or ".") / f"timetable_helper{src.suffix}"
        if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
            shutil.copy2(src, dst)
        return dst
    except Exception:
        return None


def main() -> None:
    # 任务栏分组用独立 ID，否则 Windows 会按 pythonw.exe 分组、显示 Python 的图标
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Ristt.TimetableHelper.2026")
    except Exception:
        pass
    root = tk.Tk()
    # 窗口图标：任务栏和 Alt-Tab 都认这个，不然显示成 Tk 的羽毛
    ico = HERE / "时间表助手.ico"
    ico_tk = _ascii_icon(ico)
    if ico_tk is not None:
        # 注意：光用 default= 只改「以后新建窗口」的默认图标，当前窗口不变，
        # 所以必须对当前窗口直接设一次，再补 default 让后续弹窗也用同一个。
        try:
            root.iconbitmap(str(ico_tk))
        except Exception:
            pass
        try:
            root.iconbitmap(default=str(ico_tk))
        except Exception:
            pass
    # 只走 iconbitmap 这一条：iconphoto 的优先级比它高，而 PNG 在 16px 标题栏上
    # 显示不出来，结果反而回落到 Tk 默认的羽毛图标（实测踩过）。
    try:
        app = App(root)
    except Exception:
        messagebox.showerror("启动失败", traceback.format_exc())
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
