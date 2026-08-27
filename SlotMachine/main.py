"""Modern Slot Machine — a three-reel slot game with a draggable lever.

Built with Python 3.12 + CustomTkinter for a modern Windows app look.

Features:
  - continuous-strip reels with a raised-cosine speed profile (slow start,
    gradual acceleration, peak, gentle stop, exact landing on the payline)
  - 5 paylines (top / middle / bottom / 2 diagonals), per-reel strips
  - cumulative jackpot and free-spin rounds
  - auto-spin (AUTO) and click-a-reel-to-stop
  - English / Chinese UI toggle
  - win particle effects
  - config.json tuning, save.json persistence, RTP display
  - retro sound effects with mute toggle
  - DPI-aware window that auto-fits the screen height

Run:    python main.py
Build:  powershell -ExecutionPolicy Bypass -File .\\build_exe.ps1

Version: 0.6.0
"""

from __future__ import annotations

import ctypes
import json
import math
import os
import random
import sys
import time
import tkinter as tk
from dataclasses import dataclass
from typing import Any

import customtkinter as ctk

__version__ = "0.6.0"

# ---------------------------------------------------------------------------
# DPI awareness & timer resolution (before the Tk window is created)
# ---------------------------------------------------------------------------


def _enable_dpi_awareness() -> None:
    """Ask Windows for per-monitor DPI awareness so text stays crisp."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor aware
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # system aware
        except Exception:
            pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _enable_high_resolution_timer() -> None:
    """Give Tk's after() callbacks ~1 ms resolution on Windows so the reel
    animation frames arrive evenly instead of in ~15 ms jittery bursts."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass


_enable_dpi_awareness()
_enable_high_resolution_timer()
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ---------------------------------------------------------------------------
# Paths, config & theme
# ---------------------------------------------------------------------------

BG = "#0F1020"
CARD = "#1B1C33"
CARD_LIGHT = "#24263F"
BORDER = "#343656"
TEXT = "#EDEFF7"
MUTED = "#8A8FAF"
ACCENT = "#7C8CFF"
GOLD = "#FFD166"
GREEN = "#5EE6A5"
RED = "#FF6B6B"

FONT = "Segoe UI"
FONT_EMOJI = "Segoe UI Emoji"


def _app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def _resource_path(relative: str) -> str:
    """Resolve a path that also works inside a PyInstaller one-file build."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)


DEFAULT_CONFIG: dict[str, Any] = {
    "starting_credits": 1000,
    "bet_min": 5,
    "bet_max": 100,
    "bet_step": 5,
    "jackpot_fee": 0.02,      # share of each paid bet that feeds the jackpot
    "jackpot_seed": 500,      # jackpot resets to this value after it is won
    "free_spin_count": 3,     # spins awarded on a triple diamond line
    "pair_line_only": True,   # pairs pay only on the middle line
    "pair_symbol_max_mult": 3,  # pairs pay only for symbols with this multiplier or less
    "pair_factor": 0.35,      # pair payout = round(multiplier x this)
    "auto_spin_delay": 0.9,   # seconds between auto spins
    "free_spin_wild_count": 1,  # wilds added to each reel during free spins
    "symbols": [
        {"name": "Cherry", "emoji": "🍒", "multiplier": 2, "weight": 10},
        {"name": "Lemon", "emoji": "🍋", "multiplier": 3, "weight": 9},
        {"name": "Orange", "emoji": "🍊", "multiplier": 4, "weight": 8},
        {"name": "Bell", "emoji": "🔔", "multiplier": 6, "weight": 6},
        {"name": "Star", "emoji": "⭐", "multiplier": 10, "weight": 4},
        {"name": "Seven", "emoji": "7", "multiplier": 20, "weight": 3},
        {"name": "Diamond", "emoji": "💎", "multiplier": 60, "weight": 2},
        {"name": "Wild", "emoji": "✨", "multiplier": 25, "weight": 1},
    ],
    # one physical strip per reel (indices into symbols)
    "reel_strips": [
        [2, 1, 1, 1, 3, 1, 5, 0, 3, 0, 1, 1, 0, 0, 0, 4, 0, 3, 2, 3, 0, 0, 2, 2, 4, 6, 4, 2, 5, 1],
        [2, 1, 4, 3, 2, 3, 0, 2, 0, 3, 1, 3, 0, 5, 0, 1, 0, 0, 1, 2, 1, 1, 5, 2, 0, 0, 4, 1, 4, 6],
        [1, 0, 4, 1, 1, 2, 2, 0, 5, 0, 4, 0, 0, 1, 1, 2, 0, 3, 1, 1, 4, 0, 2, 3, 3, 6, 5, 0, 2, 3],
    ],
}


def load_config() -> dict[str, Any]:
    """Load config.json next to the app; write defaults on first run."""
    path = os.path.join(_app_dir(), "config.json")
    cfg = dict(DEFAULT_CONFIG)
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            cfg.update({k: v for k, v in loaded.items() if k in DEFAULT_CONFIG})
    except Exception:
        pass
    try:
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return cfg


CONFIG = load_config()


@dataclass(frozen=True)
class Symbol:
    name: str
    emoji: str
    multiplier: int  # three-of-a-kind pays multiplier x bet
    weight: int      # probability weight (informational)


SYMBOLS = tuple(Symbol(**s) for s in CONFIG["symbols"])
REEL_STRIPS = tuple(tuple(s) for s in CONFIG["reel_strips"])
PAIR_LINE_ONLY = bool(CONFIG.get("pair_line_only", True))
PAIR_SYMBOL_MAX_MULT = int(CONFIG.get("pair_symbol_max_mult", 3))
PAIR_FACTOR = float(CONFIG.get("pair_factor", 0.35))
AUTO_SPIN_DELAY = float(CONFIG.get("auto_spin_delay", 0.9))
WILD_IDX = len(SYMBOLS) - 1
FREE_SPIN_WILD_COUNT = int(CONFIG.get("free_spin_wild_count", 1))
DIAMOND_IDX = max(range(len(SYMBOLS)), key=lambda i: SYMBOLS[i].multiplier)
# wilds may substitute for any symbol except the jackpot/scatter diamond
_WILD_CHOICES = tuple(i for i in range(len(SYMBOLS)) if i != DIAMOND_IDX)


def _with_extra_wilds(strip: tuple[int, ...], count: int) -> tuple[int, ...]:
    """Replace the first `count` cherries with wilds (free-spin reels)."""
    out = list(strip)
    added = 0
    for i, sym in enumerate(out):
        if sym == 0 and added < count:
            out[i] = WILD_IDX
            added += 1
    return tuple(out)


FREE_SPIN_STRIPS = tuple(_with_extra_wilds(s, FREE_SPIN_WILD_COUNT) for s in REEL_STRIPS)

# payline rows: top = -1, middle = 0, bottom = +1 (per reel)
PAYLINES = (
    (0, 0, 0),      # middle
    (-1, -1, -1),   # top
    (1, 1, 1),      # bottom
    (-1, 0, 1),     # diagonal top-left -> bottom-right
    (1, 0, -1),     # diagonal bottom-left -> top-right
)
ROW_LABELS = ("MID", "TOP", "BOTTOM", "DIAG↘", "DIAG↗")


def _payout_plain(r0: int, r1: int, r2: int, allow_pair: bool) -> tuple[int, str, int | None]:
    """Payout for a line without wilds."""
    if r0 == r1 == r2:
        return SYMBOLS[r0].multiplier, "THREE", r0
    if allow_pair and (r0 == r1 or r0 == r2 or r1 == r2):
        idx = r0 if r0 == r1 or r0 == r2 else r1
        if SYMBOLS[idx].multiplier <= PAIR_SYMBOL_MAX_MULT:
            return max(1, round(SYMBOLS[idx].multiplier * PAIR_FACTOR)), "PAIR", idx
    return 0, "NONE", None


def _payout_units(r0: int, r1: int, r2: int, allow_pair: bool = True) -> tuple[int, str, int | None]:
    """Payout with wild substitution: each wild picks the best symbol."""
    if WILD_IDX not in (r0, r1, r2):
        return _payout_plain(r0, r1, r2, allow_pair)
    best = (0, "NONE", None)
    rng0 = _WILD_CHOICES if r0 == WILD_IDX else (r0,)
    rng1 = _WILD_CHOICES if r1 == WILD_IDX else (r1,)
    rng2 = _WILD_CHOICES if r2 == WILD_IDX else (r2,)
    for a in rng0:
        for b in rng1:
            for c in rng2:
                u, k, s = _payout_plain(a, b, c, allow_pair)
                if u > best[0]:
                    best = (u, k, s)
    return best


def compute_rtp() -> float:
    """Theoretical return-to-player % from the configured strips (per spin)."""
    sizes = [len(s) for s in REEL_STRIPS]
    total_combos = sizes[0] * sizes[1] * sizes[2]
    expected = 0.0
    for line_idx, line in enumerate(PAYLINES):
        allow_pair = line_idx == 0 or not PAIR_LINE_ONLY
        for i in range(sizes[0]):
            for j in range(sizes[1]):
                for k in range(sizes[2]):
                    units, _, _ = _payout_units(
                        REEL_STRIPS[0][i], REEL_STRIPS[1][j], REEL_STRIPS[2][k],
                        allow_pair=allow_pair,
                    )
                    expected += units
    return expected / total_combos * 100.0


RTP = compute_rtp()

# reel geometry (pixels, logical)
REEL_W = 108
REEL_H = 148
REEL_SPACING = 46
REEL_FONT_PAY = 40
REEL_FONT_OFF = 28

# lever geometry (pixels, logical)
LEVER_W = 110
LEVER_H = 190

# ---------------------------------------------------------------------------
# Localization (English / Chinese)
# ---------------------------------------------------------------------------

L10N: dict[str, dict[str, str]] = {
    "en": {
        "title": "🎰 SLOT MACHINE",
        "subtitle": "5 lines · jackpot · free spins",
        "credits": "CREDITS",
        "bet": "BET",
        "jackpot": "JACKPOT 🏆 {amount:,}",
        "reset_credits": "Reset credits",
        "spin": "SPIN",
        "auto_btn": "AUTO",
        "lang_btn": "中",
        "paytable_title": "PAYTABLE · 5 lines · 3OAK ×N · pair ×1 mid (low) · ✨ wild in free spins",
        "stats": "Spins {spins} · Win {rate}% · Best +{best:,} · RTP ≈ {rtp}% · Actual {actual}%",
        "status_pull": "🎰 Pull the lever to spin!",
        "status_pulling": "Pulling the lever…",
        "status_spinning": "Spinning…",
        "status_free_spin": "FREE SPIN {n}/{total} · Spinning…",
        "status_win": "WIN +{amount:,} ({lines}){streak} 🎉",
        "streak": " · streak ×{n}",
        "status_jackpot": "💎 JACKPOT +{amount:,} · {n} FREE SPINS! 💎",
        "status_near_miss": "So close — try again!",
        "status_scatter": "✨ SCATTER! {n} FREE SPINS!",
        "status_lose": "No luck — pull again!",
        "status_no_credits": "Not enough credits — press Reset to keep playing",
        "status_reset": "Credits reset — pull the lever!",
        "status_auto_next": "AUTO · next spin…",
        "status_auto_stopped": "AUTO stopped — not enough credits",
        "pull": "PULL",
        "row_mid": "MID",
        "row_top": "TOP",
        "row_bottom": "BOTTOM",
        "row_diag1": "DIAG↘",
        "row_diag2": "DIAG↗",
        "detail_scatter": "SCATTER {n} FREE SPINS",
        "detail_jackpot": "JACKPOT +{amount:,}",
        "settings": "Settings",
        "sound": "Sound",
        "on": "On",
        "off": "Off",
        "volume": "Volume",
        "vol_low": "Low",
        "vol_med": "Med",
        "vol_high": "High",
        "language": "Language",
        "auto_delay": "Auto spin delay",
        "delay_fast": "Fast",
        "delay_std": "Std",
        "delay_slow": "Slow",
        "reset_stats": "Reset stats",
        "stats_reset": "Stats reset",
        "close": "Close",
    },
    "zh": {
        "title": "🎰 老虎机",
        "subtitle": "5 条线 · 大奖 · 免费转",
        "credits": "积分",
        "bet": "下注",
        "jackpot": "奖池 🏆 {amount:,}",
        "reset_credits": "重置积分",
        "spin": "开始",
        "auto_btn": "自动",
        "lang_btn": "EN",
        "paytable_title": "赔率表 · 5 条线 · 三连 ×N · 对子 ×1（仅中线低倍）· ✨ 免费转 Wild",
        "stats": "局数 {spins} · 胜率 {rate}% · 最高 +{best:,} · 返奖率 ≈ {rtp}% · 实际 {actual}%",
        "status_pull": "🎰 拉下拉杆开始！",
        "status_pulling": "拉动拉杆…",
        "status_spinning": "转动中…",
        "status_free_spin": "免费转 {n}/{total} · 转动中…",
        "status_win": "赢了 +{amount:,}（{lines}）{streak}🎉",
        "streak": " · 连胜 ×{n}",
        "status_jackpot": "💎 大奖 +{amount:,} · 免费转 {n} 次！💎",
        "status_near_miss": "差一点！再试一次！",
        "status_scatter": "✨ 集齐钻石！免费转 {n} 次！",
        "status_lose": "没中，再拉一次！",
        "status_no_credits": "积分不足——按重置继续",
        "status_reset": "积分已重置——拉下拉杆！",
        "status_auto_next": "自动转 · 下一局…",
        "status_auto_stopped": "自动转已停止——积分不足",
        "pull": "拉",
        "row_mid": "中",
        "row_top": "上",
        "row_bottom": "下",
        "row_diag1": "斜↘",
        "row_diag2": "斜↗",
        "detail_scatter": "集齐 {n} 次免费转",
        "detail_jackpot": "大奖 +{amount:,}",
        "settings": "设置",
        "sound": "音效",
        "on": "开",
        "off": "关",
        "volume": "音量",
        "vol_low": "低",
        "vol_med": "中",
        "vol_high": "高",
        "language": "语言",
        "auto_delay": "自动转间隔",
        "delay_fast": "快",
        "delay_std": "标准",
        "delay_slow": "慢",
        "reset_stats": "重置统计",
        "stats_reset": "统计已重置",
        "close": "关闭",
    },
}

ROW_L10N_KEY = {
    "MID": "row_mid",
    "TOP": "row_top",
    "BOTTOM": "row_bottom",
    "DIAG↘": "row_diag1",
    "DIAG↗": "row_diag2",
}

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------


class SlotMachineApp(ctk.CTk):
    STARTING_CREDITS = int(CONFIG.get("starting_credits", 1000))
    BET_MIN = int(CONFIG.get("bet_min", 5))
    BET_MAX = int(CONFIG.get("bet_max", 100))
    BET_STEP = int(CONFIG.get("bet_step", 5))
    JACKPOT_FEE = float(CONFIG.get("jackpot_fee", 0.02))
    JACKPOT_SEED = int(CONFIG.get("jackpot_seed", 500))
    FREE_SPIN_COUNT = int(CONFIG.get("free_spin_count", 3))
    FRAME_MS = 10  # ~100 fps reel animation (with 1 ms timer resolution)

    def __init__(self) -> None:
        super().__init__()
        self.configure(fg_color=BG)
        self.title("🎰 Slot Machine")
        self.resizable(False, False)

        # CustomTkinter detects the monitor DPI automatically; raw canvas
        # widgets are not covered by that scaling, so we track it ourselves.
        self._scale = self._window_dpi_scale()

        self.diamond_idx = max(range(len(SYMBOLS)), key=lambda i: SYMBOLS[i].multiplier)

        # game state
        save = self._load_save()
        self.credits = int(save.get("credits", self.STARTING_CREDITS))
        self.bet = max(self.BET_MIN, min(self.BET_MAX, int(save.get("bet", 10))))
        self.mute = bool(save.get("mute", False))
        self.volume = max(1, min(3, int(save.get("volume", 2))))
        self.auto_delay = max(0.3, min(3.0, float(save.get("auto_delay", AUTO_SPIN_DELAY))))
        self.lang = save.get("lang", "en")
        if self.lang not in L10N:
            self.lang = "en"
        self.jackpot = int(save.get("jackpot", self.JACKPOT_SEED))
        self.stats = {
            "spins": int(save.get("stats", {}).get("spins", 0)),
            "wins": int(save.get("stats", {}).get("wins", 0)),
            "best": int(save.get("stats", {}).get("best", 0)),
        }
        self.win_streak = 0
        self.free_spins = 0
        self.auto = False
        self._auto_job: str | None = None

        self.spinning = False
        self.finished_reels = 0

        self._lever_progress = 0.0
        self._lever_pressed = False
        self._lever_pulling = False
        self._lever_drag_start = 0
        self._flash_jobs: list[str] = []

        self._particles: list[dict] = []
        self._particle_items: dict[Any, list[int]] = {}

        self.reel_canvases: list[tk.Canvas] = []
        self._active_strips = REEL_STRIPS
        # integer offsets => symbols exactly on the payline from the first frame
        self._reel_final = [random.randrange(len(s)) for s in REEL_STRIPS]
        self._reel_highlight = [False, False, False]
        self._win_rows: set[tuple[int, int]] = set()
        self._reel_anim: list[dict] = [None, None, None]

        self._build_ui()
        self._bind_shortcuts()

        try:
            self.iconbitmap(_resource_path(os.path.join("assets", "icon.ico")))
        except Exception:
            pass

        for i in range(3):
            self._draw_reel(i, self._reel_final[i])
        self._draw_lever(0.0)
        self._update_jackpot_label()
        self._update_stats_label()
        self._set_status(self._txt("status_pull"), MUTED)

        # fit the window to the available screen height (never overflow);
        # CTk's geometry() treats sizes as logical and scales them itself,
        # so convert the physical measured values back to logical first.
        self.update_idletasks()
        req_h = int(self.winfo_reqheight() / self._scale)
        max_h = int((self.winfo_screenheight() - 100) / self._scale)
        win_h = min(req_h, max_h)
        self.geometry(f"620x{win_h}")

        # center the window on screen (position offsets are physical pixels)
        self.update_idletasks()
        win_w_px = int(620 * self._scale)
        win_h_px = int(win_h * self._scale)
        pos_x = max(0, (self.winfo_screenwidth() - win_w_px) // 2)
        pos_y = max(0, (self.winfo_screenheight() - win_h_px) // 2)
        self.geometry(f"+{pos_x}+{pos_y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _window_dpi_scale(self) -> float:
        """Monitor DPI scale for this window, mirroring CustomTkinter (1.0 = 100%)."""
        try:
            from ctypes import pointer, windll, wintypes

            hwnd = wintypes.HWND(self.winfo_id())
            monitor = windll.user32.MonitorFromWindow(hwnd, wintypes.DWORD(2))
            x_dpi, y_dpi = wintypes.UINT(), wintypes.UINT()
            windll.shcore.GetDpiForMonitor(monitor, 0, pointer(x_dpi), pointer(y_dpi))
            return (x_dpi.value + y_dpi.value) / 192.0
        except Exception:
            return 1.0

    # ------------------------------------------------------- localization

    def _txt(self, key: str, **kw) -> str:
        try:
            return L10N[self.lang][key].format(**kw)
        except Exception:
            return L10N["en"][key]

    def _apply_language(self) -> None:
        self.title_label.configure(text=self._txt("title"))
        self.subtitle_label.configure(text=self._txt("subtitle"))
        self.credits_caption.configure(text=self._txt("credits"))
        self.bet_caption.configure(text=self._txt("bet"))
        self.reset_btn.configure(text=self._txt("reset_credits"))
        self.spin_btn.configure(text=self._txt("spin"))
        self.auto_btn.configure(text=self._txt("auto_btn"))
        self.lang_btn.configure(text=self._txt("lang_btn"))
        self.paytable_title.configure(text=self._txt("paytable_title"))
        self._sync_auto_button()
        self._update_jackpot_label()
        self._update_stats_label()
        self._draw_lever(self._lever_progress)
        if not self.spinning and not self._lever_pulling:
            self._set_status(self._txt("status_pull"), MUTED)

    def _toggle_lang(self) -> None:
        self.lang = "zh" if self.lang == "en" else "en"
        self._apply_language()
        self._save()

    # ------------------------------------------------------------ settings

    def _open_settings(self) -> None:
        win = ctk.CTkToplevel(self)
        win.title(self._txt("settings"))
        win.configure(fg_color=BG)
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        ctk.CTkLabel(
            win,
            text=self._txt("settings"),
            font=ctk.CTkFont(family=FONT, size=16, weight="bold"),
            text_color=TEXT,
        ).pack(pady=(14, 4))

        # sound on/off
        def set_sound(enable: bool) -> None:
            self.mute = not enable
            self.mute_btn.configure(text="🔊" if not self.mute else "🔇")
            sound_btn.configure(
                text=f"{self._txt('sound')}: {self._txt('on' if not self.mute else 'off')}"
            )
            self._save()

        sound_btn = ctk.CTkButton(
            win,
            text="",
            width=230,
            height=30,
            corner_radius=10,
            fg_color=CARD_LIGHT,
            hover_color="#31345A",
            text_color=TEXT,
            font=ctk.CTkFont(family=FONT, size=12),
            command=lambda: set_sound(self.mute),
        )
        sound_btn.pack(pady=(6, 2))
        set_sound(not self.mute)

        # volume
        ctk.CTkLabel(
            win,
            text=self._txt("volume"),
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=MUTED,
        ).pack(pady=(8, 2))
        vol_labels = (self._txt("vol_low"), self._txt("vol_med"), self._txt("vol_high"))
        vol_values = {label: i + 1 for i, label in enumerate(vol_labels)}
        vol_seg = ctk.CTkSegmentedButton(
            win,
            values=list(vol_labels),
            command=lambda v: self._set_volume(vol_values[v]),
            width=230,
            height=28,
        )
        vol_seg.set(vol_labels[self.volume - 1])
        vol_seg.pack(pady=2)

        # language
        ctk.CTkLabel(
            win,
            text=self._txt("language"),
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=MUTED,
        ).pack(pady=(8, 2))
        lang_seg = ctk.CTkSegmentedButton(
            win,
            values=("English", "中文"),
            command=self._change_lang,
            width=230,
            height=28,
        )
        lang_seg.set("English" if self.lang == "en" else "中文")
        lang_seg.pack(pady=2)

        # auto-spin delay
        ctk.CTkLabel(
            win,
            text=self._txt("auto_delay"),
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=MUTED,
        ).pack(pady=(8, 2))
        delay_options = (("delay_fast", 0.5), ("delay_std", 0.9), ("delay_slow", 1.5))
        delay_labels = [self._txt(k) for k, _ in delay_options]
        delay_values = {label: value for label, (_, value) in zip(delay_labels, delay_options)}
        delay_seg = ctk.CTkSegmentedButton(
            win,
            values=delay_labels,
            command=lambda v: self._set_auto_delay(delay_values[v]),
            width=230,
            height=28,
        )
        delay_seg.set(
            delay_labels[min(range(len(delay_options)), key=lambda i: abs(delay_options[i][1] - self.auto_delay))]
        )
        delay_seg.pack(pady=2)

        # reset stats
        ctk.CTkButton(
            win,
            text=self._txt("reset_stats"),
            command=self._reset_stats,
            width=230,
            height=30,
            corner_radius=10,
            fg_color=CARD_LIGHT,
            hover_color="#3A2B33",
            text_color=RED,
            font=ctk.CTkFont(family=FONT, size=12),
        ).pack(pady=(12, 4))

        ctk.CTkButton(
            win,
            text=self._txt("close"),
            command=win.destroy,
            width=230,
            height=30,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color="#6677E8",
            text_color=TEXT,
            font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
        ).pack(pady=(2, 14))

        win.bind("<Escape>", lambda _e: win.destroy())
        win.update_idletasks()
        s = int(self._scale)
        win_w = max(260, win.winfo_reqwidth() // s)
        win_h = max(220, win.winfo_reqheight() // s)
        pos_x = self.winfo_rootx() + (self.winfo_width() - win_w * s) // 2
        pos_y = self.winfo_rooty() + (self.winfo_height() - win_h * s) // 2
        win.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")

    def _set_volume(self, level: int) -> None:
        self.volume = max(1, min(3, level))
        self._save()

    def _set_auto_delay(self, seconds: float) -> None:
        self.auto_delay = max(0.3, min(3.0, seconds))
        self._save()

    def _change_lang(self, label: str) -> None:
        new_lang = "zh" if label == "中文" else "en"
        if new_lang == self.lang:
            return
        self.lang = new_lang
        self._apply_language()
        self._save()
        # rebuild the settings dialog in the new language
        for child in self.winfo_children():
            if isinstance(child, ctk.CTkToplevel):
                child.destroy()
        self._open_settings()

    def _reset_stats(self) -> None:
        self.stats = {"spins": 0, "wins": 0, "best": 0, "total_bet": 0, "total_win": 0}
        self._update_stats_label()
        self._set_status(self._txt("stats_reset"), MUTED)
        self._save()

    # ------------------------------------------------------- persistence

    def _save_path(self) -> str:
        return os.path.join(_app_dir(), "save.json")

    def _load_save(self) -> dict:
        try:
            with open(self._save_path(), "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save(self) -> None:
        data = {
            "credits": self.credits,
            "bet": self.bet,
            "mute": self.mute,
            "volume": self.volume,
            "auto_delay": self.auto_delay,
            "lang": self.lang,
            "jackpot": self.jackpot,
            "win_streak": self.win_streak,
            "stats": self.stats,
        }
        try:
            with open(self._save_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _on_close(self) -> None:
        self._cancel_auto()
        self._save()
        self.destroy()

    # ------------------------------------------------------------- UI setup

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(padx=18, pady=(12, 0), fill="x")
        self.title_label = ctk.CTkLabel(
            header,
            text=self._txt("title"),
            font=ctk.CTkFont(family=FONT, size=20, weight="bold"),
            text_color=TEXT,
        )
        self.title_label.pack()
        self.subtitle_label = ctk.CTkLabel(
            header,
            text=self._txt("subtitle"),
            font=ctk.CTkFont(family=FONT, size=11),
            text_color=MUTED,
        )
        self.subtitle_label.pack()

        self._build_machine()

        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
            text_color=MUTED,
        )
        self.status_label.pack(pady=(8, 0))
        self.detail_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family=FONT, size=10),
            text_color=MUTED,
        )
        self.detail_label.pack(pady=(0, 2))

        self._build_controls()
        self._build_paytable()
        self._build_stats_footer()
        self._update_balance()
        self._update_bet_label()

    def _build_machine(self) -> None:
        machine = ctk.CTkFrame(
            self, fg_color=CARD, corner_radius=20, border_width=1, border_color=BORDER
        )
        machine.pack(padx=18, pady=(12, 0), fill="x")

        inner = ctk.CTkFrame(machine, fg_color="transparent")
        inner.pack(padx=16, pady=14)

        reels_wrap = ctk.CTkFrame(inner, fg_color="transparent")
        reels_wrap.pack(side="left")
        for i in range(3):
            if i:
                divider = ctk.CTkFrame(
                    reels_wrap,
                    width=2,
                    height=int((REEL_H - 16) * self._scale),
                    fg_color=BORDER,
                )
                divider.pack(side="left", padx=7)
            self._make_reel(reels_wrap)

        lever_wrap = ctk.CTkFrame(inner, fg_color="transparent")
        lever_wrap.pack(side="left", padx=(24, 0))

        self.canvas = tk.Canvas(
            lever_wrap,
            width=int(LEVER_W * self._scale),
            height=int(LEVER_H * self._scale),
            bg=CARD,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_lever_press)
        self.canvas.bind("<B1-Motion>", self._on_lever_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_lever_release)

        self.spin_btn = ctk.CTkButton(
            lever_wrap,
            text=self._txt("spin"),
            command=self._start_pull,
            width=96,
            height=32,
            corner_radius=12,
            fg_color=ACCENT,
            hover_color="#6677E8",
            font=ctk.CTkFont(family=FONT, size=13, weight="bold"),
        )
        self.spin_btn.pack(pady=(8, 0))

        self.auto_btn = ctk.CTkButton(
            lever_wrap,
            text=self._txt("auto_btn"),
            command=self._toggle_auto,
            width=96,
            height=26,
            corner_radius=10,
            fg_color=CARD_LIGHT,
            hover_color="#31345A",
            text_color=TEXT,
            font=ctk.CTkFont(family=FONT, size=11, weight="bold"),
        )
        self.auto_btn.pack(pady=(6, 0))

    def _make_reel(self, parent) -> None:
        canvas = tk.Canvas(
            parent,
            width=int(REEL_W * self._scale),
            height=int(REEL_H * self._scale),
            bg="#0B0C1C",
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(side="left")
        i = len(self.reel_canvases)
        canvas.bind("<Button-1>", lambda _e, idx=i: self._stop_reel(idx))
        self.reel_canvases.append(canvas)

    def _build_controls(self) -> None:
        controls = ctk.CTkFrame(
            self, fg_color=CARD, corner_radius=18, border_width=1, border_color=BORDER
        )
        controls.pack(padx=18, pady=(10, 0), fill="x")

        # credits + jackpot
        creds = ctk.CTkFrame(controls, fg_color="transparent")
        creds.pack(side="left", padx=(14, 0), pady=10)
        self.credits_caption = ctk.CTkLabel(
            creds,
            text=self._txt("credits"),
            font=ctk.CTkFont(family=FONT, size=9),
            text_color=MUTED,
        )
        self.credits_caption.pack(anchor="w")
        self.balance_label = ctk.CTkLabel(
            creds,
            text="",
            font=ctk.CTkFont(family=FONT, size=22, weight="bold"),
            text_color=TEXT,
        )
        self.balance_label.pack(anchor="w")
        self.jackpot_label = ctk.CTkLabel(
            creds,
            text="",
            font=ctk.CTkFont(family=FONT, size=10, weight="bold"),
            text_color=GOLD,
        )
        self.jackpot_label.pack(anchor="w", pady=(1, 0))
        self.reset_btn = ctk.CTkButton(
            creds,
            text=self._txt("reset_credits"),
            command=self._reset_credits,
            width=88,
            height=20,
            fg_color="transparent",
            hover_color=CARD_LIGHT,
            text_color=MUTED,
            corner_radius=8,
            font=ctk.CTkFont(family=FONT, size=9),
        )
        self.reset_btn.pack(anchor="w", pady=(2, 0))

        # bet
        bet_box = ctk.CTkFrame(controls, fg_color="transparent")
        bet_box.pack(side="left", padx=(30, 0), pady=10)
        self.bet_caption = ctk.CTkLabel(
            bet_box,
            text=self._txt("bet"),
            font=ctk.CTkFont(family=FONT, size=9),
            text_color=MUTED,
        )
        self.bet_caption.pack()
        row = ctk.CTkFrame(bet_box, fg_color="transparent")
        row.pack(pady=(2, 0))
        minus = ctk.CTkButton(
            row,
            text="−",
            command=lambda: self._change_bet(-self.BET_STEP),
            width=30,
            height=26,
            corner_radius=9,
            fg_color=CARD_LIGHT,
            hover_color="#31345A",
            text_color=TEXT,
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
        )
        minus.pack(side="left")
        self.bet_label = ctk.CTkLabel(
            row,
            text="",
            width=44,
            font=ctk.CTkFont(family=FONT, size=17, weight="bold"),
            text_color=TEXT,
        )
        self.bet_label.pack(side="left")
        plus = ctk.CTkButton(
            row,
            text="+",
            command=lambda: self._change_bet(self.BET_STEP),
            width=30,
            height=26,
            corner_radius=9,
            fg_color=CARD_LIGHT,
            hover_color="#31345A",
            text_color=TEXT,
            font=ctk.CTkFont(family=FONT, size=14, weight="bold"),
        )
        plus.pack(side="left")

        # settings + language + mute toggles
        self.settings_btn = ctk.CTkButton(
            controls,
            text="⚙",
            command=self._open_settings,
            width=40,
            height=30,
            corner_radius=10,
            fg_color=CARD_LIGHT,
            hover_color="#31345A",
            text_color=TEXT,
            font=ctk.CTkFont(family=FONT, size=14),
        )
        self.settings_btn.pack(side="left", padx=(24, 6), pady=10)

        self.lang_btn = ctk.CTkButton(
            controls,
            text=self._txt("lang_btn"),
            command=self._toggle_lang,
            width=40,
            height=30,
            corner_radius=10,
            fg_color=CARD_LIGHT,
            hover_color="#31345A",
            text_color=TEXT,
            font=ctk.CTkFont(family=FONT, size=12, weight="bold"),
        )
        self.lang_btn.pack(side="left", padx=(0, 6), pady=10)

        self.mute_btn = ctk.CTkButton(
            controls,
            text="🔊" if not self.mute else "🔇",
            command=self._toggle_mute,
            width=40,
            height=30,
            corner_radius=10,
            fg_color=CARD_LIGHT,
            hover_color="#31345A",
            text_color=TEXT,
            font=ctk.CTkFont(family=FONT_EMOJI, size=14),
        )
        self.mute_btn.pack(side="left", padx=(0, 14), pady=10)

    def _build_paytable(self) -> None:
        paytable = ctk.CTkFrame(
            self, fg_color=CARD, corner_radius=14, border_width=1, border_color=BORDER
        )
        paytable.pack(padx=18, pady=(8, 0), fill="x")
        self.paytable_title = ctk.CTkLabel(
            paytable,
            text=self._txt("paytable_title"),
            font=ctk.CTkFont(family=FONT, size=10),
            text_color=MUTED,
        )
        self.paytable_title.pack(pady=(8, 6))
        row = ctk.CTkFrame(paytable, fg_color="transparent")
        row.pack(pady=(0, 8))
        for sym in SYMBOLS:
            cell = ctk.CTkFrame(
                row, fg_color=CARD_LIGHT, corner_radius=9, width=52, height=44
            )
            cell.pack_propagate(False)
            cell.pack(side="left", padx=2)
            ctk.CTkLabel(
                cell,
                text=sym.emoji,
                font=ctk.CTkFont(family=FONT_EMOJI, size=18),
                text_color="#FFFFFF",
            ).pack(pady=(4, 0))
            ctk.CTkLabel(
                cell,
                text=f"×{sym.multiplier}",
                font=ctk.CTkFont(family=FONT, size=10, weight="bold"),
                text_color=GOLD,
            ).pack()

    def _build_stats_footer(self) -> None:
        self.stats_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family=FONT, size=10),
            text_color=MUTED,
        )
        self.stats_label.pack(pady=(6, 14))

    # ------------------------------------------------------------ reel engine

    def _draw_reel(self, i: int, offset: float, wobble_px: float = 0.0) -> None:
        """Draw one reel as a continuous strip visible through the window."""
        c = self.reel_canvases[i]
        c.delete("all")
        s = self._scale
        w = int(REEL_W * s)
        h = int(REEL_H * s)
        mid = h / 2.0
        spacing = REEL_SPACING * s
        strip = self._active_strips[i]
        n = len(strip)
        base = int(offset)
        frac = offset - base

        c.create_rectangle(0, 0, w, h, fill="#0B0C1C", outline="")

        # visible symbols (one above / one below the payline, like a real reel)
        for k in range(-2, 3):
            idx = strip[(base + k) % n]
            sym = SYMBOLS[idx]
            y = mid + (k - frac) * spacing + wobble_px
            if y < -40 * s or y > h + 40 * s:
                continue
            winning = (i, k) in self._win_rows
            if k == 0 and not winning:
                size, color = REEL_FONT_PAY, "#FFFFFF"
            elif winning:
                size, color = REEL_FONT_PAY, GOLD
            else:
                size, color = REEL_FONT_OFF, "#6F7396"
            c.create_text(
                w / 2.0,
                y,
                text=sym.emoji,
                font=(FONT_EMOJI, -int(size * s)),
                fill=color,
            )

        # glass shading at the top and bottom edges
        band = int(12 * s)
        c.create_rectangle(0, 0, w, band, fill="#0A0B1A", outline="")
        c.create_rectangle(0, h - band, w, h, fill="#0A0B1A", outline="")

        # three payline rows (top / middle / bottom); winners turn gold
        for row in (-1, 0, 1):
            y = mid + row * spacing
            if (i, row) in self._win_rows:
                color, width = GOLD, int(2 * s)
            elif row == 0:
                color, width = "#3E3A55", 1
            else:
                color, width = "#2B2D48", 1
            c.create_line(5 * s, y, w - 5 * s, y, fill=color, width=width)

        c.create_rectangle(1, 1, w - 1, h - 1, outline="#2A2C47", width=int(2 * s))

    def _begin_spin(self) -> None:
        self._lever_pulling = False
        self.spinning = True
        self.finished_reels = 0
        self._active_strips = (
            FREE_SPIN_STRIPS if getattr(self, "_free_spin_no", 0) > 0 else REEL_STRIPS
        )
        self._reel_highlight = [False, False, False]
        self._win_rows = set()
        self._cancel_flash_jobs()
        self._clear_particles()
        self.detail_label.configure(text="")

        if getattr(self, "_free_spin_no", 0) > 0:
            self._set_status(
                self._txt("status_free_spin", n=self._free_spin_no, total=self.FREE_SPIN_COUNT),
                GREEN,
            )
        else:
            self._set_status(self._txt("status_spinning"), ACCENT)

        # longer, gentler animation: reels stop one by one, reel 0 first.
        durations = (3.5, 4.5, 5.5)
        for i in range(3):
            strip_len = len(self._active_strips[i])
            stop_idx = random.randrange(strip_len)
            rotations = random.randint(3, 5)
            end_offset = stop_idx + rotations * strip_len
            distance = end_offset - self._reel_final[i]

            self._reel_anim[i] = {
                "start": time.monotonic() + i * 0.12,
                "duration": durations[i],
                "start_offset": self._reel_final[i],
                "end_offset": end_offset,
                "distance": distance,
                "done": False,
            }
            self.after(self.FRAME_MS, self._spin_reel_frame, i)

    def _spin_reel_frame(self, i: int) -> None:
        st = self._reel_anim[i]
        if st is None or st["done"]:
            return
        now = time.monotonic()
        if now < st["start"]:
            self.after(self.FRAME_MS, self._spin_reel_frame, i)
            return

        t = now - st["start"]
        T = st["duration"]
        if t >= T:
            offset = st["end_offset"]
        else:
            # raised-cosine velocity profile: starts from rest, accelerates
            # smoothly to peak speed in the middle, then decelerates and
            # stops; offset lands exactly on end_offset at t == T.
            p = t / T
            offset = st["start_offset"] + st["distance"] * (
                1.0 - math.cos(math.pi * p)
            ) / 2.0
        self._draw_reel(i, offset)

        if t < T:
            self.after(self.FRAME_MS, self._spin_reel_frame, i)
        else:
            st["done"] = True
            self._reel_final[i] = st["end_offset"]
            self._draw_reel(i, st["end_offset"])
            self._wobble_reel(i, st["end_offset"])
            self._play_sound("tick")
            self.finished_reels += 1
            if self.finished_reels == 3:
                self._evaluate()

    def _stop_reel(self, i: int) -> None:
        """Click-to-stop: snap reel i to its final position immediately."""
        st = self._reel_anim[i]
        if st is None or st["done"] or not self.spinning:
            return
        st["done"] = True
        self._reel_final[i] = st["end_offset"]
        self._draw_reel(i, st["end_offset"])
        self._wobble_reel(i, st["end_offset"])
        self._play_sound("tick")
        self.finished_reels += 1
        if self.finished_reels == 3:
            self._evaluate()

    def _wobble_reel(self, i: int, base_offset: float) -> None:
        """Small damped oscillation when a reel settles, like a real machine."""
        start = time.monotonic()

        def step() -> None:
            t = time.monotonic() - start
            amp = 1.8 * self._scale * math.exp(-t * 8.0) * math.sin(2 * math.pi * 6.0 * t)
            self._draw_reel(i, base_offset, wobble_px=amp)
            if abs(amp) > 0.2 * self._scale:
                self.after(self.FRAME_MS, step)
            else:
                self._draw_reel(i, base_offset)

        step()

    def _row_symbol(self, reel_i: int, row: int) -> int:
        strip = self._active_strips[reel_i]
        n = len(strip)
        return strip[int(math.floor(self._reel_final[reel_i] + row)) % n]

    def _reel_symbols(self) -> list[int]:
        return [self._row_symbol(i, 0) for i in range(3)]

    def _near_miss(self) -> bool:
        """Two reels matching with the third just off the line (no payout)."""
        for line_idx, line in enumerate(PAYLINES):
            rows = [self._row_symbol(i, line[i]) for i in range(3)]
            allow_pair = line_idx == 0 or not PAIR_LINE_ONLY
            units, _, _ = _payout_units(*rows, allow_pair=allow_pair)
            if units > 0:
                continue  # this line already pays
            for a, b in ((0, 1), (0, 2), (1, 2)):
                if rows[a] == rows[b]:
                    c = 3 - a - b
                    target = rows[a]
                    if (
                        self._row_symbol(c, line[c] + 1) == target
                        or self._row_symbol(c, line[c] - 1) == target
                    ):
                        return True
        return False

    def _evaluate(self) -> None:
        self.spinning = False
        results: list[tuple[str, int, list[tuple[int, int]], int]] = []
        jackpot_hit = False

        for line_idx, line in enumerate(PAYLINES):
            rows = [self._row_symbol(i, line[i]) for i in range(3)]
            allow_pair = line_idx == 0 or not PAIR_LINE_ONLY
            units, _, win_sym = _payout_units(*rows, allow_pair=allow_pair)
            if units > 0:
                cells = [(i, line[i]) for i in range(3)]
                results.append((ROW_LABELS[line_idx], units, cells, win_sym))
                if win_sym == self.diamond_idx:
                    jackpot_hit = True

        total_units = sum(r[1] for r in results)
        payout = total_units * self.bet

        # scatter: 3+ diamonds anywhere in the visible 3x3 window award free spins
        scatter = 0
        for i in range(3):
            for row in (-1, 0, 1):
                if self._row_symbol(i, row) == self.diamond_idx:
                    scatter += 1

        if jackpot_hit:
            payout += self.jackpot
        if scatter >= 3:
            self.free_spins = self.FREE_SPIN_COUNT

        winning_cells: set[tuple[int, int]] = set()
        for _, _, cells, _ in results:
            winning_cells.update(cells)

        if payout > 0:
            self.credits += payout
            self.stats["total_win"] = self.stats.get("total_win", 0) + payout
            self.win_streak += 1
            self.stats["wins"] += 1
            self.stats["best"] = max(self.stats["best"], payout)
            old = self.credits - payout
            self._animate_balance(old, self.credits)
            self._flash_balance(GREEN if jackpot_hit else GOLD)
            self._flash_win_rows(winning_cells)
            self._spawn_win_particles(winning_cells)
            self._show_detail(results, payout, jackpot_hit, scatter)

            if jackpot_hit:
                self._set_status(
                    self._txt(
                        "status_jackpot",
                        amount=payout,
                        n=self.FREE_SPIN_COUNT,
                    ),
                    GREEN,
                )
                self._play_sound("jackpot")
            else:
                lines_txt = " + ".join(
                    self._txt(ROW_L10N_KEY.get(r[0], "row_mid")) for r in results
                )
                streak_txt = (
                    self._txt("streak", n=self.win_streak) if self.win_streak > 1 else ""
                )
                self._set_status(
                    self._txt("status_win", amount=payout, lines=lines_txt, streak=streak_txt),
                    GOLD,
                )
                self._play_sound("win")

            if jackpot_hit:
                self.jackpot = self.JACKPOT_SEED
                self._update_jackpot_label()
        else:
            self.win_streak = 0
            if scatter >= 3:
                self.detail_label.configure(
                    text=self._txt("detail_scatter", n=self.FREE_SPIN_COUNT)
                )
                self._set_status(
                    self._txt("status_scatter", n=self.FREE_SPIN_COUNT), GREEN
                )
                self._play_sound("win")
            elif self._near_miss():
                self.detail_label.configure(text="")
                self._set_status(self._txt("status_near_miss"), ACCENT)
            else:
                self.detail_label.configure(text="")
                self._set_status(self._txt("status_lose"), MUTED)
            self._play_sound("lose")

        self.stats["spins"] += 1
        self._update_stats_label()
        self._save()
        self._active_strips = REEL_STRIPS

        if self.auto:
            self._auto_job = self.after(int(self.auto_delay * 1000), self._start_pull)

    def _show_detail(
        self,
        results: list[tuple[str, int, list[tuple[int, int]], int]],
        payout: int,
        jackpot_hit: bool,
        scatter: int,
    ) -> None:
        """Per-spin settlement detail line, e.g. 'MID 🍒×3 +20 · TOP ✨🍒🍒×3 +40'."""
        parts = []
        for label, units, _, win_sym in results:
            sym = SYMBOLS[win_sym]
            count = "×3" if units == sym.multiplier else "×2"
            parts.append(f"{self._txt(ROW_L10N_KEY.get(label, 'row_mid'))} {sym.emoji}{count} +{units * self.bet}")
        if scatter >= 3:
            parts.append(self._txt("detail_scatter", n=self.FREE_SPIN_COUNT))
        if jackpot_hit:
            parts.append(self._txt("detail_jackpot", amount=self.jackpot))
        self.detail_label.configure(text="  ·  ".join(parts))

    # ------------------------------------------------------- lever & actions

    def _lever_handle_pos(self, progress: float | None = None) -> tuple[float, float]:
        if progress is None:
            progress = self._lever_progress
        s = self._scale
        x = LEVER_W / 2.0 * s - progress * 6 * s
        y = (52 + progress * 58) * s
        return x, y

    def _on_lever_press(self, event) -> None:
        if self.spinning or self._lever_pulling:
            return
        hx, hy = self._lever_handle_pos()
        if (event.x - hx) ** 2 + (event.y - hy) ** 2 <= (40 * self._scale) ** 2:
            self._lever_pressed = True
            self._lever_drag_start = event.y

    def _on_lever_drag(self, event) -> None:
        if not self._lever_pressed or self._lever_pulling:
            return
        if event.y - self._lever_drag_start > 30 * self._scale:
            self._start_pull()

    def _on_lever_release(self, event) -> None:
        if not self._lever_pressed:
            return
        self._lever_pressed = False
        if not self._lever_pulling and not self.spinning:
            self._start_pull()

    def _start_pull(self) -> None:
        if self.spinning or self._lever_pulling:
            return
        if self.free_spins == 0 and self.credits < self.bet:
            self._flash_balance(RED)
            if self.auto:
                self._toggle_auto_off()
                self._set_status(self._txt("status_auto_stopped"), RED)
            else:
                self._set_status(self._txt("status_no_credits"), RED)
            return

        if self.free_spins > 0:
            self._free_spin_no = self.free_spins
            self.free_spins -= 1
        else:
            self.credits -= self.bet
            self.stats["total_bet"] = self.stats.get("total_bet", 0) + self.bet
            self.jackpot += max(1, round(self.bet * self.JACKPOT_FEE))
            self._update_jackpot_label()
        self._update_balance()

        self._lever_pulling = True
        self._set_status(self._txt("status_pulling"), MUTED)
        self._play_sound("spin")
        self._tween(0.0, 1.0, 220, self._draw_lever, self._on_lever_down)

    def _on_lever_down(self) -> None:
        self._tween(1.0, 0.0, 220, self._draw_lever, self._begin_spin)

    # ------------------------------------------------------------- auto spin

    def _toggle_auto(self) -> None:
        self.auto = not self.auto
        if self.auto:
            if not self.spinning and not self._lever_pulling:
                self._set_status(self._txt("status_auto_next"), ACCENT)
        else:
            self._cancel_auto()
        self._sync_auto_button()
        self._save()

    def _toggle_auto_off(self) -> None:
        self.auto = False
        self._cancel_auto()
        self._sync_auto_button()

    def _sync_auto_button(self) -> None:
        if self.auto:
            self.auto_btn.configure(fg_color=GOLD, text_color="#141414")
        else:
            self.auto_btn.configure(fg_color=CARD_LIGHT, text_color=TEXT)

    def _cancel_auto(self) -> None:
        if self._auto_job is not None:
            try:
                self.after_cancel(self._auto_job)
            except Exception:
                pass
            self._auto_job = None

    # ------------------------------------------------------------ particles

    def _spawn_win_particles(self, cells: set[tuple[int, int]]) -> None:
        if not cells:
            return
        s = self._scale
        colors = (GOLD, "#FFF3C4", "#FFB347", "#FF7B54")
        for i, row in cells:
            canvas = self.reel_canvases[i]
            mid = (REEL_H / 2.0) * s
            y0 = mid + row * REEL_SPACING * s
            for _ in range(7):
                self._particles.append({
                    "canvas": canvas,
                    "x": random.uniform(12, REEL_W * s - 12),
                    "y": y0 + random.uniform(-8, 8) * s,
                    "vx": random.uniform(-42, 42) * s,
                    "vy": random.uniform(-95, -35) * s,
                    "life": random.uniform(0.45, 0.95),
                    "age": 0.0,
                    "size": random.uniform(1.5, 3.2) * s,
                    "color": random.choice(colors),
                })
        self._particle_step()

    def _particle_step(self) -> None:
        for canvas, items in self._particle_items.items():
            for item in items:
                canvas.delete(item)
        self._particle_items = {}

        dt = self.FRAME_MS / 1000.0
        alive: list[dict] = []
        for p in self._particles:
            p["age"] += dt
            if p["age"] >= p["life"]:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 260 * self._scale * dt
            frac = p["age"] / p["life"]
            radius = p["size"] * (1.0 - frac)
            if radius < 0.4:
                continue
            item = p["canvas"].create_oval(
                p["x"] - radius,
                p["y"] - radius,
                p["x"] + radius,
                p["y"] + radius,
                fill=p["color"],
                outline="",
            )
            self._particle_items.setdefault(p["canvas"], []).append(item)
            alive.append(p)

        self._particles = alive
        if self._particles:
            self.after(self.FRAME_MS, self._particle_step)

    def _clear_particles(self) -> None:
        for canvas, items in self._particle_items.items():
            for item in items:
                canvas.delete(item)
        self._particle_items = {}
        self._particles = []

    # ------------------------------------------------------------ UI helpers

    def _update_balance(self) -> None:
        self.balance_label.configure(text=f"{self.credits:,}")

    def _animate_balance(self, start: int, target: int) -> None:
        steps = 24

        def tick(i: int = 0) -> None:
            if i >= steps:
                self.balance_label.configure(text=f"{target:,}")
                return
            val = int(start + (target - start) * (i / steps))
            self.balance_label.configure(text=f"{val:,}")
            self.after(20, tick, i + 1)

        tick()

    def _update_bet_label(self) -> None:
        self.bet_label.configure(text=f"{self.bet}")

    def _update_jackpot_label(self) -> None:
        self.jackpot_label.configure(text=self._txt("jackpot", amount=self.jackpot))

    def _update_stats_label(self) -> None:
        spins = self.stats["spins"]
        win_rate = 100.0 * self.stats["wins"] / spins if spins else 0.0
        total_bet = self.stats.get("total_bet", 0)
        total_win = self.stats.get("total_win", 0)
        actual = 100.0 * total_win / total_bet if total_bet > 0 else 0.0
        self.stats_label.configure(
            text=self._txt(
                "stats",
                spins=spins,
                rate=f"{win_rate:.0f}",
                best=self.stats["best"],
                rtp=f"{RTP:.0f}",
                actual=f"{actual:.0f}",
            )
        )

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.configure(text=text, text_color=color)

    def _change_bet(self, delta: int) -> None:
        new_bet = max(self.BET_MIN, min(self.BET_MAX, self.bet + delta))
        if new_bet != self.bet:
            self.bet = new_bet
            self._update_bet_label()
            self._save()

    def _reset_credits(self) -> None:
        if self.spinning:
            return
        self.credits = self.STARTING_CREDITS
        self._update_balance()
        self._set_status(self._txt("status_reset"), MUTED)
        self._save()

    def _toggle_mute(self) -> None:
        self.mute = not self.mute
        self.mute_btn.configure(text="🔊" if not self.mute else "🔇")
        self._save()

    def _flash_balance(self, color: str) -> None:
        self.balance_label.configure(text_color=color)
        self._flash_jobs.append(
            self.after(900, lambda: self.balance_label.configure(text_color=TEXT))
        )

    def _flash_win_rows(self, cells: set[tuple[int, int]]) -> None:
        self._win_rows = set(cells)
        for i in range(3):
            self._draw_reel(i, self._reel_final[i])
        self._flash_jobs.append(self.after(1400, self._restore_reels))

    def _restore_reels(self) -> None:
        self._win_rows = set()
        for i in range(3):
            self._draw_reel(i, self._reel_final[i])

    def _cancel_flash_jobs(self) -> None:
        for job in self._flash_jobs:
            try:
                self.after_cancel(job)
            except Exception:
                pass
        self._flash_jobs.clear()
        self._restore_reels()

    def _play_sound(self, name: str) -> None:
        if self.mute or sys.platform != "win32":
            return
        try:
            import winsound

            if self.volume >= 3:
                fname = f"{name}.wav"
            elif self.volume == 2:
                fname = f"{name}_med.wav"
            else:
                fname = f"{name}_low.wav"
            path = _resource_path(os.path.join("assets", "sounds", fname))
            if os.path.exists(path):
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass

    def _tween(
        self,
        start: float,
        end: float,
        duration: int,
        update,
        on_done,
    ) -> None:
        steps = max(1, int(duration / 16))
        step_size = (end - start) / steps
        current = [start]

        def tick(count: int = 0) -> None:
            if count >= steps:
                update(end)
                on_done()
                return
            current[0] += step_size
            update(current[0])
            self.after(16, tick, count + 1)

        tick()

    def _draw_lever(self, progress: float) -> None:
        self._lever_progress = progress
        c = self.canvas
        c.delete("all")
        s = self._scale
        w = int(LEVER_W * s)
        h = int(LEVER_H * s)
        px, py = LEVER_W / 2.0 * s, h - 40 * s
        hx, hy = self._lever_handle_pos(progress)

        # pivot / mount base
        c.create_oval(
            px - 34 * s, py - 24 * s, px + 34 * s, py + 24 * s,
            fill="#2A2C47", outline=BORDER, width=int(2 * s),
        )
        c.create_oval(
            px - 24 * s, py - 15 * s, px + 24 * s, py + 15 * s,
            fill="#33355A", outline="",
        )
        c.create_oval(
            px - 13 * s, py - 8 * s, px + 13 * s, py + 8 * s,
            fill="#454875", outline="",
        )

        # lever arm: shadow, metal, highlight
        c.create_line(px, py, hx, hy, width=int(11 * s), fill="#191B33", capstyle=tk.ROUND)
        c.create_line(px, py, hx, hy, width=int(7 * s), fill="#AEB6C6", capstyle=tk.ROUND)
        c.create_line(px, py, hx, hy, width=int(2.5 * s), fill="#E8EDF5", capstyle=tk.ROUND)

        # red handle ball with highlight
        r = 16 * s
        c.create_oval(
            hx - r, hy - r, hx + r, hy + r,
            fill="#C42F3F", outline="#7E1B28", width=int(2 * s),
        )
        c.create_oval(
            hx - r + 4 * s, hy - r + 4 * s, hx + r - 5 * s, hy + r - 5 * s,
            fill="#F2555F", outline="",
        )
        c.create_arc(
            hx - r + 5 * s,
            hy - r + 5 * s,
            hx + r - 6 * s,
            hy + r - 6 * s,
            start=200,
            extent=130,
            style=tk.ARC,
            outline="#FFC7CB",
            width=int(2 * s),
        )

        c.create_text(
            w // 2, h - 9 * s, text=self._txt("pull"), fill=MUTED,
            font=(FONT, -int(10 * s), "bold"),
        )

    def _bind_shortcuts(self) -> None:
        self.bind("<space>", lambda _e: self._start_pull())
        self.bind("<Return>", lambda _e: self._start_pull())
        self.bind("<m>", lambda _e: self._toggle_mute())
        self.bind("<a>", lambda _e: self._toggle_auto())
        self.bind("<l>", lambda _e: self._toggle_lang())
        self.bind("<r>", lambda _e: self._reset_credits())
        self.bind("<plus>", lambda _e: self._change_bet(self.BET_STEP))
        self.bind("<minus>", lambda _e: self._change_bet(-self.BET_STEP))


def main() -> None:
    app = SlotMachineApp()
    app.mainloop()


if __name__ == "__main__":
    main()
