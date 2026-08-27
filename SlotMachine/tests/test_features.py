"""Feature tests for SlotMachine.

Covers payout rules (incl. wild substitution), 5 paylines, jackpot, scatter
free spins, near-miss, RTP, language, auto-spin, click-to-stop, particles,
settings, actual-RTP tracking and save/load persistence.

Run from the project root:  python tests/test_features.py
"""

import json
import os
import sys

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, APP_DIR)

SAVE = os.path.join(APP_DIR, "save.json")
backup = None
if os.path.exists(SAVE):
    with open(SAVE, "r", encoding="utf-8") as f:
        backup = f.read()
    os.remove(SAVE)

import main


def restore() -> None:
    try:
        if backup is None:
            if os.path.exists(SAVE):
                os.remove(SAVE)
        else:
            with open(SAVE, "w", encoding="utf-8") as f:
                f.write(backup)
    except Exception as exc:
        print("save restore failed:", exc)


passed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global passed
    if cond:
        passed += 1
        print("PASS", name)
    else:
        print("FAIL", name, detail)
        restore()
        sys.exit(1)


W = main.WILD_IDX
D = main.DIAMOND_IDX

# ---------------------------------------------------------------- payouts
u, kind, _ = main._payout_units(0, 0, 0)
check("triple cherry = 2 units", u == 2 and kind == "THREE")
u, kind, _ = main._payout_units(D, D, D)
check("triple diamond = 60 units", u == 60)
u, kind, _ = main._payout_units(0, 0, 2)
check("cherry pair pays 1 unit", u == 1 and kind == "PAIR")
u, _, _ = main._payout_units(0, 0, 2, allow_pair=False)
check("pair not paid on side lines", u == 0)
u, _, _ = main._payout_units(2, 2, 0)
check("orange pair (high symbol) not paid", u == 0)
u, _, _ = main._payout_units(0, 0, 6)
check("cherry pair with diamond third pays", u == 1)

# wild substitution
u, kind, sym = main._payout_units(0, 0, W)
check("wild completes cherry triple", u == 2 and kind == "THREE" and sym == 0)
u, kind, sym = main._payout_units(W, W, W)
check("triple wild pays wild multiplier", u == 25 and sym == W)
u, kind, _ = main._payout_units(0, W, 2)
check("wild picks best pair on middle", u == 1 and kind == "PAIR")
u, _, _ = main._payout_units(0, W, 2, allow_pair=False)
check("wild pair not paid on side lines", u == 0)
u, _, _ = main._payout_units(W, D, W)
check("wild cannot substitute for diamond", u == 1)

check("base strips have no wilds", all(s.count(W) == 0 for s in main.REEL_STRIPS))
check("free-spin strips add one wild", all(s.count(W) == 1 for s in main.FREE_SPIN_STRIPS))
check("free-spin strips keep 30 slots",
      all(len(s) == 30 for s in main.FREE_SPIN_STRIPS))
check("RTP in healthy range", 88 <= main.RTP <= 96, f"RTP={main.RTP:.2f}")


def first_idx(strip: tuple, value: int) -> int:
    return next(i for i, x in enumerate(strip) if x == value)


app = main.SlotMachineApp()
app.update()
check("initial credits from config", app.credits == app.STARTING_CREDITS)
check("jackpot seeded", app.jackpot == app.JACKPOT_SEED)
check("initial reel offsets are integers", all(o == int(o) for o in app._reel_final))


def set_reels(offsets: list[int]) -> None:
    app._reel_final = [float(o) for o in offsets]
    app.spinning = False
    app.free_spins = 0
    app._win_rows = set()


# middle-line triple cherry -> +2x bet
c0 = app.credits
set_reels([first_idx(main.REEL_STRIPS[i], 0) for i in range(3)])
app._evaluate()
check("middle triple cherry pays 2x bet", app.credits == c0 + 2 * app.bet,
      f"credits {c0} -> {app.credits}")

# cherry pair on middle line + bell third -> +1x bet
c0 = app.credits
set_reels([7, 6, 17])
app._evaluate()
check("cherry pair pays 1x bet", app.credits == c0 + 1 * app.bet,
      f"credits {c0} -> {app.credits}")

# triple diamond on middle line -> 60x bet + jackpot, free spins, jackpot reset
c0 = app.credits
jp0 = app.jackpot
set_reels([25, 29, 25])
app._evaluate()
check("jackpot payout", app.credits == c0 + 60 * app.bet + jp0,
      f"credits {c0} -> {app.credits}, expected +{60 * app.bet + jp0}")
check("free spins awarded", app.free_spins == app.FREE_SPIN_COUNT,
      f"free_spins={app.free_spins}")
check("jackpot reset to seed", app.jackpot == app.JACKPOT_SEED,
      f"jackpot={app.jackpot}")

# scatter without a line win: diamonds on (0,0),(1,+1),(2,-1) -> free spins
c0 = app.credits
set_reels([25, 28, 26])
app._evaluate()
check("scatter keeps credits unchanged", app.credits == c0)
check("scatter awards free spins", app.free_spins == app.FREE_SPIN_COUNT,
      f"free_spins={app.free_spins}")
check("scatter status shown", "SCATTER" in app.status_label.cget("text"),
      app.status_label.cget("text"))

# near-miss: two stars on a line, third just off it, no payout anywhere
set_reels([28, 13, 7])
app._evaluate()
check("near-miss detected", app._near_miss())
check("near-miss shows no win status", "So close" in app.status_label.cget("text"),
      app.status_label.cget("text"))

# actual RTP tracking
bet_before = app.stats.get("total_bet", 0)
app.free_spins = 0
app.mute = True
app._start_pull()
check("paid spin adds to total_bet", app.stats.get("total_bet", 0) == bet_before + app.bet,
      f"{bet_before} -> {app.stats.get('total_bet')}")
app._lever_pulling = False
app.spinning = False

win_before = app.stats.get("total_win", 0)
set_reels([first_idx(main.REEL_STRIPS[i], 0) for i in range(3)])
app._evaluate()
check("win adds to total_win", app.stats.get("total_win", 0) == win_before + 2 * app.bet,
      f"{win_before} -> {app.stats.get('total_win')}")
check("detail line shows combo", "MID" in app.detail_label.cget("text"),
      app.detail_label.cget("text"))

# free spin does not deduct credits
app.free_spins = 1
credits_before = app.credits
app._start_pull()
check("free spin not charged", app.credits == credits_before and app.free_spins == 0,
      f"credits {credits_before} -> {app.credits}, free_spins={app.free_spins}")
app._lever_pulling = False
app.spinning = False

# --------------------------------------------------------- language toggle
app._apply_language()
check("default language is English", app.lang == "en")
check("english title shown", "SLOT MACHINE" in app.title_label.cget("text"))
app._toggle_lang()
check("language switched to zh", app.lang == "zh")
check("chinese title shown", "老虎机" in app.title_label.cget("text"))
app._set_status(app._txt("status_pull"), main.MUTED)
check("chinese status shown", "拉下拉杆" in app.status_label.cget("text"),
      app.status_label.cget("text"))
app._toggle_lang()
check("language switched back to en", app.lang == "en")

# ------------------------------------------------------------ auto toggle
app._toggle_auto()
check("auto enabled", app.auto is True)
app._toggle_auto()
check("auto disabled", app.auto is False and app._auto_job is None)

# auto stops itself when credits run out
app.auto = True
app._sync_auto_button()
credits_saved = app.credits
app.credits = 0
app.free_spins = 0
app._start_pull()
check("auto turns off when no credits", app.auto is False)
check("no credits status shown", "credits" in app.status_label.cget("text").lower(),
      app.status_label.cget("text"))
app.credits = credits_saved
app._update_balance()

# --------------------------------------------------------- click to stop
app.spinning = True
app.finished_reels = 0
app._reel_anim = [
    {"done": False, "end_offset": 80.0},
    {"done": True, "end_offset": 81.0},
    {"done": True, "end_offset": 82.0},
]
app._stop_reel(0)
check("click-to-stop snaps reel", app._reel_anim[0]["done"] is True)
check("click-to-stop counts reel", app.finished_reels == 1)
check("stopped reel lands on integer", app._reel_final[0] == 80.0)
app.spinning = False
app.finished_reels = 0
app._reel_anim = [None, None, None]

# ------------------------------------------------------------- particles
app._spawn_win_particles({(0, 0), (1, 0), (2, 0)})
check("particles spawned", len(app._particles) > 0)
app._clear_particles()
check("particles cleared", len(app._particles) == 0)

# --------------------------------------------------------------- settings
check("default volume is medium", app.volume == 2)
for name in ("spin", "tick", "win", "jackpot", "lose"):
    base = os.path.join(APP_DIR, "assets", "sounds", f"{name}.wav")
    med = os.path.join(APP_DIR, "assets", "sounds", f"{name}_med.wav")
    low = os.path.join(APP_DIR, "assets", "sounds", f"{name}_low.wav")
    check(f"sound variants exist ({name})",
          os.path.exists(base) and os.path.exists(med) and os.path.exists(low))

app._set_volume(1)
check("volume set to low", app.volume == 1)
app._set_volume(3)
check("volume set to high", app.volume == 3)
app._set_volume(2)
check("volume back to medium", app.volume == 2)

app._set_auto_delay(1.5)
check("auto delay set", app.auto_delay == 1.5)
app._set_auto_delay(0.9)
check("auto delay restored", app.auto_delay == 0.9)

app._reset_stats()
check("stats reset",
      app.stats == {"spins": 0, "wins": 0, "best": 0, "total_bet": 0, "total_win": 0})

app._open_settings()
app.update()
toplevels = [c for c in app.winfo_children() if isinstance(c, main.ctk.CTkToplevel)]
check("settings window opens", len(toplevels) == 1)
for w in toplevels:
    w.destroy()

app._change_lang("中文")
check("settings can switch to zh", app.lang == "zh")
for c in app.winfo_children():
    if isinstance(c, main.ctk.CTkToplevel):
        c.destroy()
app._change_lang("English")
check("settings can switch back to en", app.lang == "en")
for c in app.winfo_children():
    if isinstance(c, main.ctk.CTkToplevel):
        c.destroy()

app.destroy()

# ---------------------------------------------------------------- save/load
app2 = main.SlotMachineApp()
app2.update()
app2.credits = 777
app2.bet = 25
app2._save()
with open(os.path.join(APP_DIR, "save.json"), "r", encoding="utf-8") as f:
    saved = json.load(f)
check("save file written", saved.get("credits") == 777 and saved.get("bet") == 25,
      str(saved))
app2.destroy()

app3 = main.SlotMachineApp()
app3.update()
check("save loaded on restart", app3.credits == 777 and app3.bet == 25,
      f"credits={app3.credits}, bet={app3.bet}")
app3.destroy()

restore()
print(f"ALL {passed} FEATURE TESTS PASSED")
