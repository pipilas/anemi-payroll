#!/usr/bin/env python3
"""
Stamhad Payroll — Payroll & Tip Management Application  (v5)
Fixes: per-row wage calculation for dual positions, tab order (Emp/Hours/Tips),
labor cost in week view, button styling overhaul, FOH/BOH dropdown,
Grand Total renamed to Total Labor.
"""

import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json, csv, os, random, string, copy, platform, traceback
from datetime import datetime, timedelta, date
from pathlib import Path

# ── Windows DPI fix: make GUI crisp on high-DPI displays ────────────────────
if platform.system() == "Windows":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
try:
    _VERSION = (Path(__file__).parent / "version.txt").read_text().strip()
except Exception:
    _VERSION = "0.0.0"
APP_TITLE    = f"Stamhad Payroll v{_VERSION}"
MIN_W, MIN_H = 1040, 740
BASE_DIR     = Path(__file__).parent
CONFIG_DIR   = BASE_DIR / "config"
EMP_FILE     = CONFIG_DIR / "employees.json"
POS_FILE     = CONFIG_DIR / "positions.json"

DAYS   = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SHIFTS = ["Morning", "Brunch", "Dinner"]

IS_MAC   = platform.system() == "Darwin"
IS_LINUX = platform.system() == "Linux"

if IS_MAC:
    FONT = "Helvetica Neue"
elif IS_LINUX:
    FONT = "Ubuntu"
else:
    FONT = "Segoe UI"

# ─── Colour Palette ──────────────────────────────────────────────────────────
BG_PAGE   = "#F0F2F5"
BG_CARD   = "#FFFFFF"
BG_NAV    = "#1B2A4A"
BG_INPUT  = "#FFFFFF"
BORDER    = "#E5E7EB"
BORDER_LT = "#F3F4F6"
BORDER_FOCUS = "#4F46E5"

FG        = "#1C1C1E"
FG_SEC    = "#6B7280"
FG_HDR    = "#374151"

ACCENT    = "#4F46E5"
ACCENT_HV = "#4338CA"
SUCCESS   = "#10B981"
SUCCESS_HV = "#059669"
SUCCESS_BG = "#D1FAE5"
SUCCESS_FG = "#065F46"
WARN_BG   = "#FEF3C7"
WARN_FG   = "#92400E"
WARN_BORD = "#F59E0B"
WARN_HV   = "#D97706"
DANGER    = "#EF4444"
DANGER_HV = "#DC2626"
EXPORT_BG = "#0891B2"
EXPORT_HV = "#0E7490"
CANCEL_BG = "#FFFFFF"
CANCEL_FG = "#374151"
CANCEL_BD = "#D1D5DB"
CANCEL_HV = "#E5E7EB"
TOTAL_LABOR_BG = "#F0F9FF"

FOH_BG    = "#3B82F6"
FOH_FG    = "#FFFFFF"
BOH_BG    = "#F97316"
BOH_FG    = "#FFFFFF"

SHIFT_CLR = {"Morning": ("#FCD34D", "#78350F"),
             "Brunch":  ("#34D399", "#064E3B"),
             "Dinner":  ("#818CF8", "#312E81")}

ROW_A     = "#FFFFFF"
ROW_B     = "#EEF1F4"

DEPT_OPTIONS = ["Front of House (FOH)", "Back of House (BOH)"]
DEPT_MAP = {"Front of House (FOH)": "FOH", "Back of House (BOH)": "BOH",
            "FOH": "FOH", "BOH": "BOH"}
DEPT_DISPLAY = {"FOH": "Front of House (FOH)", "BOH": "Back of House (BOH)"}

# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def gen_id(n=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

def monday_of(d=None):
    d = d or date.today()
    return d - timedelta(days=d.weekday())

def week_dir(mon):
    return BASE_DIR / f"week_{mon.isoformat()}"

def fmt(v):
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"

def safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ═══════════════════════════════════════════════════════════════════════════════
#  SCROLLABLE FRAME
# ═══════════════════════════════════════════════════════════════════════════════
class ScrollFrame(tk.Frame):
    def __init__(self, parent, bg=BG_PAGE):
        self._outer = tk.Frame(parent, bg=bg)
        self.canvas = tk.Canvas(self._outer, bg=bg, highlightthickness=0, bd=0)
        self.vsb = tk.Scrollbar(self._outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        super().__init__(self.canvas, bg=bg)
        self._win_id = self.canvas.create_window((0, 0), window=self, anchor="nw")

        self.bind("<Configure>", self._on_inner_cfg)
        self.canvas.bind("<Configure>", self._on_canvas_cfg)
        self._bind_scroll_recursive(self)
        self._bind_scroll_recursive(self.canvas)

    def _on_inner_cfg(self, _):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_cfg(self, e):
        self.canvas.itemconfig(self._win_id, width=e.width)

    def _bind_scroll_recursive(self, widget):
        if IS_MAC:
            widget.bind("<MouseWheel>", self._wheel, add="+")
        else:
            widget.bind("<MouseWheel>", self._wheel, add="+")
            widget.bind("<Button-4>", self._wheel_linux, add="+")
            widget.bind("<Button-5>", self._wheel_linux, add="+")

    def _wheel(self, e):
        if IS_MAC:
            self.canvas.yview_scroll(int(-e.delta), "units")
        else:
            self.canvas.yview_scroll(int(-e.delta / 120), "units")

    def _wheel_linux(self, e):
        self.canvas.yview_scroll(-3 if e.num == 4 else 3, "units")

    def pack(self, **kw):
        self._outer.pack(**kw)

    def grid(self, **kw):
        self._outer.grid(**kw)

    def place(self, **kw):
        self._outer.place(**kw)

    def destroy(self):
        if getattr(self, "_destroying", False):
            return
        self._destroying = True
        self._outer.destroy()

    def bind_child(self, widget):
        self._bind_scroll_recursive(widget)


# ═══════════════════════════════════════════════════════════════════════════════
#  STYLED WIDGETS  — full colour button styles
# ═══════════════════════════════════════════════════════════════════════════════
class Btn(tk.Frame):
    """Label-based button — renders bg color correctly on macOS."""
    STYLES = {
        "primary":  (ACCENT,    "#FFFFFF", ACCENT_HV),
        "success":  (SUCCESS,   "#FFFFFF", SUCCESS_HV),
        "danger":   (DANGER,    "#FFFFFF", DANGER_HV),
        "export":   (EXPORT_BG, "#FFFFFF", EXPORT_HV),
        "cancel":   ("#FFFFFF", "#374151",  "#E5E7EB"),
        "warning":  (WARN_BORD, "#FFFFFF", WARN_HV),
        "ghost":    ("#FFFFFF", "#374151",  "#E5E7EB"),
        "outline":  ("#FFFFFF", ACCENT,    "#EEF2FF"),
    }

    def __init__(self, parent, text="", command=None, style="primary", **kw):
        bg, fg, hv = self.STYLES.get(style, self.STYLES["primary"])
        super().__init__(parent, bg=bg, highlightbackground=bg,
                         highlightthickness=1, cursor="hand2")
        self._bg, self._fg, self._hv = bg, fg, hv
        self._cmd = command
        self._lbl = tk.Label(self, text=text, bg=bg, fg=fg,
                             font=(FONT, 11, "bold"), padx=16, pady=8,
                             cursor="hand2")
        self._lbl.pack()
        for w in (self, self._lbl):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Button-1>", self._on_click)

    def _on_enter(self, _):
        self.config(bg=self._hv, highlightbackground=self._hv)
        self._lbl.config(bg=self._hv)

    def _on_leave(self, _):
        self.config(bg=self._bg, highlightbackground=self._bg)
        self._lbl.config(bg=self._bg)

    def _on_click(self, _):
        if self._cmd:
            self._cmd()

    def config(self, **kw):
        if "bg" in kw:
            self._bg = kw["bg"]
            self._lbl.config(bg=kw["bg"])
            super().config(bg=kw["bg"], highlightbackground=kw.get("highlightbackground", kw["bg"]))
        if "fg" in kw:
            self._fg = kw["fg"]
            self._lbl.config(fg=kw["fg"])
        if "text" in kw:
            self._lbl.config(text=kw["text"])
        if "highlightbackground" in kw and "bg" not in kw:
            super().config(highlightbackground=kw["highlightbackground"])
        if "relief" in kw:
            pass  # ignore, we handle our own look
        if "bd" in kw:
            pass  # ignore

    configure = config

    def cget(self, key):
        if key == "text":
            return self._lbl.cget("text")
        return super().cget(key)


class Inp(tk.Entry):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_INPUT, fg=FG, insertbackground=FG,
                         relief="flat", font=(FONT, 12), bd=0,
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=BORDER_FOCUS, **kw)


class DeptPill(tk.Label):
    def __init__(self, parent, dept, **kw):
        is_foh = str(dept).upper().startswith("F")
        super().__init__(parent, text=" FOH " if is_foh else " BOH ",
                         bg=FOH_BG if is_foh else BOH_BG,
                         fg=FOH_FG if is_foh else BOH_FG,
                         font=(FONT, 9, "bold"), padx=5, pady=1, **kw)


class ShiftPill(tk.Label):
    def __init__(self, parent, shift_name, **kw):
        bg, fg = SHIFT_CLR.get(shift_name, ("#D1D5DB", "#374151"))
        super().__init__(parent, text=f" {shift_name} ", bg=bg, fg=fg,
                         font=(FONT, 8, "bold"), padx=4, pady=1, **kw)


class Card(tk.Frame):
    def __init__(self, parent, bg=BG_CARD, **kw):
        super().__init__(parent, bg=bg, highlightbackground=BORDER,
                         highlightthickness=1, padx=16, pady=12, **kw)


class SectionBar(tk.Frame):
    def __init__(self, parent, text, color=ACCENT, bg=BG_PAGE):
        super().__init__(parent, bg=bg)
        tk.Frame(self, bg=color, width=4).pack(side="left", fill="y", padx=(0, 10))
        tk.Label(self, text=text, bg=bg, fg=FG, font=(FONT, 14, "bold")).pack(side="left")


# ═══════════════════════════════════════════════════════════════════════════════
#  TOAST
# ═══════════════════════════════════════════════════════════════════════════════
class Toast:
    def __init__(self, root):
        self.root = root
        self._lbl = None

    def show(self, msg, ms=3000, bg=SUCCESS_BG, fg=SUCCESS_FG):
        if self._lbl:
            self._lbl.destroy()
        self._lbl = tk.Label(self.root, text=f"  \u2713  {msg}  ", bg=bg, fg=fg,
                             font=(FONT, 12, "bold"), padx=20, pady=10)
        self._lbl.place(relx=0.5, rely=0.0, anchor="n", y=56)
        self._lbl.lift()
        self.root.after(ms, self._hide)

    def _hide(self):
        if self._lbl:
            self._lbl.destroy()
            self._lbl = None


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
class DataManager:
    # Path for the local cache of all Firebase data
    _CACHE_FILE = CONFIG_DIR / "firebase_cache.json"

    def __init__(self, firebase_uid=None):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        print(f"[DataManager] Init with firebase_uid={firebase_uid!r}")

        # ── Firebase cloud storage (per-restaurant) ────────────────────────
        self.fb = None
        self._dirty = {
            "employees": False,
            "positions": False,
            "days": [],   # list of (mon_iso, day_name) tuples pending sync
        }
        self._sync_running = False
        self._cache = {}  # in-memory cache of all Firebase data

        if firebase_uid:
            try:
                from firebase_db import FirebaseDB
                self.fb = FirebaseDB(firebase_uid)
            except Exception as e:
                print(f"[DataManager] Firebase init failed: {e}")

        # ── Bulk download all data from Firebase on startup ────────────────
        if self.fb:
            self._bulk_download()

        # ── Load data from cache ───────────────────────────────────────────
        self.positions = self._load_positions()
        self.employees = self._load_employees()

        # ── One-time migration: upload local data to Firebase ──────────────
        if self.fb:
            try:
                local_emp = self._load_json(EMP_FILE, [])
                local_pos = self._load_json(POS_FILE, [])
                self.fb.migrate_if_needed(local_emp, local_pos)
            except Exception:
                pass

        # ── Start background sync thread ───────────────────────────────────
        if self.fb:
            self._start_background_sync()

    def _bulk_download(self):
        """Download all Firebase data in one request and store in local cache.
        Merges with any locally pending (dirty) data to prevent data loss."""
        # Load any pending dirty queue from previous session
        self._load_dirty()

        # Load existing local cache (may have unsynced data)
        local_cache = self._load_json(self._CACHE_FILE, {})

        try:
            data = self.fb.download_all()
            if data and isinstance(data, dict):
                self._cache = data

                # Merge: if we have pending dirty days, keep local version
                if self._has_pending() and local_cache:
                    print("[DataManager] Merging local pending data with download...")
                    for mon_iso, day_name in self._dirty.get("days", []):
                        week_key = mon_iso.replace("-", "_")
                        local_weeks = local_cache.get("weeks", {})
                        local_day = local_weeks.get(week_key, {}).get("days", {}).get(day_name)
                        if local_day:
                            if "weeks" not in self._cache:
                                self._cache["weeks"] = {}
                            if week_key not in self._cache["weeks"]:
                                self._cache["weeks"][week_key] = {"days": {}}
                            if "days" not in self._cache["weeks"][week_key]:
                                self._cache["weeks"][week_key]["days"] = {}
                            self._cache["weeks"][week_key]["days"][day_name] = local_day
                            print(f"[DataManager]   Kept local data for {day_name} ({mon_iso})")

                    # Keep local employees/positions if dirty
                    if self._dirty.get("employees") and local_cache.get("employees"):
                        self._cache["employees"] = local_cache["employees"]
                        print("[DataManager]   Kept local employees")
                    if self._dirty.get("positions") and local_cache.get("positions"):
                        self._cache["positions"] = local_cache["positions"]
                        print("[DataManager]   Kept local positions")

                # Persist merged cache to disk
                self._save_local(self._CACHE_FILE, self._cache)
                print(f"[DataManager] Bulk download OK — keys: {list(self._cache.keys())}")
                return
        except Exception as e:
            print(f"[DataManager] Bulk download failed: {e}")

        # Fall back to loading cache from disk
        if local_cache:
            self._cache = local_cache
            print("[DataManager] Loaded cached data from disk")
        else:
            self._cache = {}

    def _load_employees(self):
        """Load employees from local cache (populated by bulk download)."""
        # Try in-memory cache first (from bulk download)
        if self._cache.get("employees"):
            data = self._cache["employees"]
            if isinstance(data, dict):
                data = list(data.values())
            self._save_local(EMP_FILE, data)
            return data
        return self._load_json(EMP_FILE, [])

    def _load_positions(self):
        """Load positions from local cache (populated by bulk download)."""
        if self._cache.get("positions"):
            data = self._cache["positions"]
            if isinstance(data, dict):
                data = list(data.values())
            self._save_local(POS_FILE, data)
            return data
        return self._load_json(POS_FILE, [])

    @staticmethod
    def _load_json(path, default):
        try:
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load {path}: {e}")
            traceback.print_exc()
        return copy.deepcopy(default)

    @staticmethod
    def _save_local(path, data):
        """Save to local file (cache)."""
        try:
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def save_pos(self):
        # Update in-memory cache
        self._cache["positions"] = self.positions
        self._save_local(self._CACHE_FILE, self._cache)
        # Save locally as file cache
        try:
            with open(POS_FILE, "w") as f:
                json.dump(self.positions, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save positions: {e}")
        # Try immediate Firebase sync, queue on failure
        if self.fb:
            try:
                if self.fb.save_positions(self.positions):
                    self._dirty["positions"] = False
                else:
                    self._dirty["positions"] = True
            except Exception as e:
                print(f"[DataManager] Firebase save positions failed: {e}")
                self._dirty["positions"] = True
            self._persist_dirty()

    def save_emp(self):
        # Update in-memory cache
        self._cache["employees"] = self.employees
        self._save_local(self._CACHE_FILE, self._cache)
        # Save locally as file cache
        try:
            with open(EMP_FILE, "w") as f:
                json.dump(self.employees, f, indent=2)
        except Exception as e:
            print(f"[ERROR] Failed to save employees: {e}")
        # Try immediate Firebase sync, queue on failure
        if self.fb:
            try:
                if self.fb.save_employees(self.employees):
                    self._dirty["employees"] = False
                else:
                    self._dirty["employees"] = True
            except Exception as e:
                print(f"[DataManager] Firebase save employees failed: {e}")
                self._dirty["employees"] = True
            self._persist_dirty()

    # ── Dirty queue persistence ─────────────────────────────────────────
    _DIRTY_FILE = CONFIG_DIR / "pending_sync.json"

    def _persist_dirty(self):
        """Save dirty queue to disk so it survives app restart."""
        try:
            serializable = {
                "employees": self._dirty["employees"],
                "positions": self._dirty["positions"],
                "days": self._dirty["days"],
            }
            self._save_local(self._DIRTY_FILE, serializable)
        except Exception:
            pass

    def _load_dirty(self):
        """Load dirty queue from disk (from previous session)."""
        try:
            data = self._load_json(self._DIRTY_FILE, {})
            if data:
                self._dirty["employees"] = data.get("employees", False)
                self._dirty["positions"] = data.get("positions", False)
                self._dirty["days"] = data.get("days", [])
                if self._has_pending():
                    print(f"[Sync] Loaded pending sync from previous session: "
                          f"emp={self._dirty['employees']}, pos={self._dirty['positions']}, "
                          f"days={len(self._dirty['days'])}")
        except Exception:
            pass

    # ── Background sync (offline → online recovery) ─────────────────────
    def _mark_day_dirty(self, mon, day_name):
        """Mark a day as needing sync to Firebase."""
        key = (mon.isoformat() if hasattr(mon, 'isoformat') else str(mon), day_name)
        if key not in self._dirty["days"]:
            self._dirty["days"].append(key)
            print(f"[Sync] Marked dirty: {key}")
        self._persist_dirty()

    def _has_pending(self):
        """Check if there's anything that needs syncing."""
        return (self._dirty["employees"] or
                self._dirty["positions"] or
                len(self._dirty["days"]) > 0)

    def _start_background_sync(self):
        """Start a background thread that syncs pending changes every 15 seconds."""
        import threading

        def _sync_loop():
            import time
            # Do an immediate first sync attempt after 5 seconds
            time.sleep(5)
            if self._has_pending():
                self._try_sync()
            while True:
                time.sleep(15)
                if self._has_pending():
                    self._try_sync()

        t = threading.Thread(target=_sync_loop, daemon=True)
        t.start()
        print("[Sync] Background sync started (every 15s)")

    def _try_sync(self):
        """Attempt to sync all pending changes to Firebase."""
        if not self.fb or self._sync_running:
            return
        self._sync_running = True
        print("[Sync] Syncing pending changes...")

        try:
            # Sync employees
            if self._dirty["employees"]:
                try:
                    if self.fb.save_employees(self.employees):
                        self._dirty["employees"] = False
                        print("[Sync]   Employees synced")
                except Exception:
                    pass

            # Sync positions
            if self._dirty["positions"]:
                try:
                    if self.fb.save_positions(self.positions):
                        self._dirty["positions"] = False
                        print("[Sync]   Positions synced")
                except Exception:
                    pass

            # Sync dirty days (read from cache first, CSV fallback)
            synced_days = []
            for mon_iso, day_name in self._dirty["days"]:
                try:
                    week_key = mon_iso.replace("-", "_")
                    weeks = self._cache.get("weeks", {})
                    day_data = weeks.get(week_key, {}).get("days", {}).get(day_name)
                    if day_data and isinstance(day_data, dict):
                        foh = day_data.get("foh_hours", [])
                        boh = day_data.get("boh_hours", [])
                        tips = day_data.get("tips", [])
                    else:
                        # Fallback to CSV
                        mon = date.fromisoformat(mon_iso)
                        folder = self.wk(mon)
                        foh = [r for r in self.read_csv(folder / "foh_hours.csv")
                               if r.get("day") == day_name]
                        boh = [r for r in self.read_csv(folder / "boh_hours.csv")
                               if r.get("day") == day_name]
                        tips = [r for r in self.read_csv(folder / "weekly_tips.csv")
                                if r.get("day") == day_name]
                    if self.fb.save_week_day(mon_iso, day_name, foh, boh, tips):
                        synced_days.append((mon_iso, day_name))
                        print(f"[Sync]   Day {day_name} ({mon_iso}) synced")
                except Exception:
                    pass

            for d in synced_days:
                self._dirty["days"].remove(d)

            self._persist_dirty()
            if not self._has_pending():
                print("[Sync] All changes synced!")

        except Exception as e:
            print(f"[Sync] Sync error: {e}")
        finally:
            self._sync_running = False

    def ensure_wk(self, mon):
        d = week_dir(mon)
        d.mkdir(parents=True, exist_ok=True)
        return d

    def wk(self, mon):
        return week_dir(mon)

    def read_csv(self, p):
        rows = []
        if p.exists():
            with open(p, newline="") as f:
                for r in csv.DictReader(f):
                    rows.append(r)
        return rows

    def write_csv(self, p, flds, rows):
        with open(p, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=flds)
            w.writeheader()
            w.writerows(rows)

    def pos_by_name(self, n):
        for p in self.positions:
            if p["name"] == n:
                return p
        return None

    def emp_by_id(self, eid):
        for e in self.employees:
            if e["id"] == eid:
                return e
        return None

    def get_wage(self, position_name):
        pos = self.pos_by_name(position_name)
        return safe_float(pos.get("hourly_wage", 0)) if pos else 0.0

    def get_pos_field(self, position_name, field, default=0):
        pos = self.pos_by_name(position_name)
        if pos:
            return pos.get(field, default)
        return default

    def emp_dept(self, emp):
        for a in emp.get("positions", []):
            p = self.pos_by_name(a["position_name"])
            if p:
                return p.get("department", "FOH")
        return "FOH"

    def sorted_employees(self):
        foh = [e for e in self.employees if self.emp_dept(e) == "FOH"]
        boh = [e for e in self.employees if self.emp_dept(e) == "BOH"]
        foh.sort(key=lambda e: e.get("sort_order", 9999))
        boh.sort(key=lambda e: e.get("sort_order", 9999))
        return foh, boh

    def reorder_emp(self, emp, direction):
        dept = self.emp_dept(emp)
        group = [e for e in self.employees if self.emp_dept(e) == dept]
        group.sort(key=lambda e: e.get("sort_order", 9999))
        idx = None
        for i, e in enumerate(group):
            if e["id"] == emp["id"]:
                idx = i
                break
        if idx is None:
            return
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(group):
            return
        group[idx], group[new_idx] = group[new_idx], group[idx]
        for i, e in enumerate(group):
            e["sort_order"] = i
        self.save_emp()

    # ── Save day ──────────────────────────────────────────────────────────
    def save_day(self, mon, day_name, blocks, tips):
        folder = self.ensure_wk(mon)

        foh_f = ["day", "emp_id", "employee_name", "position", "shift", "hours"]
        boh_f = ["day", "emp_id", "employee_name", "position", "shift", "hours"]
        tips_f = ["day", "shift", "emp_id", "employee_name", "position",
                  "points", "floor_tip", "bar_tip", "total_tip"]

        foh_rows = [r for r in self.read_csv(folder / "foh_hours.csv") if r.get("day") != day_name]
        boh_rows = [r for r in self.read_csv(folder / "boh_hours.csv") if r.get("day") != day_name]
        tip_rows = [r for r in self.read_csv(folder / "weekly_tips.csv") if r.get("day") != day_name]

        for b in blocks:
            pos = self.pos_by_name(b["position_name"])
            dept = pos.get("department", "FOH") if pos else "FOH"
            row = {
                "day": day_name, "emp_id": b["emp_id"],
                "employee_name": b["emp_name"],
                "position": b["position_name"],
                "shift": b.get("shift", "Dinner"),
                "hours": b.get("hours", 0),
            }
            if dept == "FOH":
                foh_rows.append(row)
            else:
                boh_rows.append(row)

        self.write_csv(folder / "foh_hours.csv", foh_f, foh_rows)
        self.write_csv(folder / "boh_hours.csv", boh_f, boh_rows)

        if tips:
            for shift, td in tips.items():
                merged = {}
                for fb in td.get("floor_breakdown", []):
                    eid = fb["emp_id"]
                    merged[eid] = {
                        "day": day_name, "shift": shift, "emp_id": eid,
                        "employee_name": fb["name"], "position": fb.get("position", ""),
                        "points": fb.get("points", 0),
                        "floor_tip": round(fb["amount"], 2), "bar_tip": 0.0,
                        "total_tip": round(fb["amount"], 2),
                    }
                for bb in td.get("bar_breakdown", []):
                    eid = bb["emp_id"]
                    if eid in merged:
                        merged[eid]["bar_tip"] = round(bb["amount"], 2)
                        merged[eid]["total_tip"] = round(merged[eid]["floor_tip"] + bb["amount"], 2)
                    else:
                        merged[eid] = {
                            "day": day_name, "shift": shift, "emp_id": eid,
                            "employee_name": bb["name"], "position": bb.get("role", ""),
                            "points": 0, "floor_tip": 0.0,
                            "bar_tip": round(bb["amount"], 2),
                            "total_tip": round(bb["amount"], 2),
                        }
                tip_rows.extend(merged.values())

        self.write_csv(folder / "weekly_tips.csv", tips_f, tip_rows)

        # ── Update in-memory cache ────────────────────────────────────────
        day_foh = [r for r in foh_rows if r.get("day") == day_name]
        day_boh = [r for r in boh_rows if r.get("day") == day_name]
        day_tips = [r for r in tip_rows if r.get("day") == day_name]

        week_key = mon.isoformat().replace("-", "_")
        if "weeks" not in self._cache:
            self._cache["weeks"] = {}
        if week_key not in self._cache["weeks"]:
            self._cache["weeks"][week_key] = {"days": {}}
        if "days" not in self._cache["weeks"][week_key]:
            self._cache["weeks"][week_key]["days"] = {}
        self._cache["weeks"][week_key]["days"][day_name] = {
            "foh_hours": day_foh,
            "boh_hours": day_boh,
            "tips": day_tips,
        }
        # Persist cache to disk
        self._save_local(self._CACHE_FILE, self._cache)

        # ── Try immediate Firebase sync, queue on failure ─────────────────
        if self.fb:
            try:
                if not self.fb.save_week_day(mon.isoformat(), day_name, day_foh, day_boh, day_tips):
                    self._mark_day_dirty(mon, day_name)
            except Exception as e:
                print(f"[DataManager] Firebase save_day failed: {e}")
                self._mark_day_dirty(mon, day_name)

    def load_day(self, mon, day_name):
        # ── Try in-memory cache first (from bulk download) ─────────────────
        mon_iso = mon.isoformat() if hasattr(mon, 'isoformat') else str(mon)
        week_key = mon_iso.replace("-", "_")
        weeks = self._cache.get("weeks", {})
        if weeks and week_key in weeks:
            day_data = weeks.get(week_key, {}).get("days", {}).get(day_name)
            if day_data and isinstance(day_data, dict):
                foh = day_data.get("foh_hours", [])
                boh = day_data.get("boh_hours", [])
                tips = day_data.get("tips", [])
                if isinstance(foh, dict): foh = list(foh.values())
                if isinstance(boh, dict): boh = list(boh.values())
                if isinstance(tips, dict): tips = list(tips.values())
                return foh, boh, tips

        # ── Fall back to local CSV ─────────────────────────────────────────
        folder = self.wk(mon)
        foh = [r for r in self.read_csv(folder / "foh_hours.csv") if r.get("day") == day_name]
        boh = [r for r in self.read_csv(folder / "boh_hours.csv") if r.get("day") == day_name]
        tips = [r for r in self.read_csv(folder / "weekly_tips.csv") if r.get("day") == day_name]
        return foh, boh, tips

    # ── Compute daily labor cost for week view ────────────────────────────
    def day_labor_cost(self, mon, day_name):
        """Sum of hours * per-position wage for a single day (no tips)."""
        foh, boh, _ = self.load_day(mon, day_name)
        total = 0.0
        for r in foh + boh:
            hrs = safe_float(r.get("hours", 0))
            wage = self.get_wage(r.get("position", ""))
            total += hrs * wage
        return total

    # ── Payroll — PER-ROW wage calculation ────────────────────────────────
    def gen_payroll(self, mon):
        # Load all days from Firebase/local via load_day (not raw CSV)
        foh = []
        boh = []
        tips = []
        for day_name in DAYS:
            day_foh, day_boh, day_tips = self.load_day(mon, day_name)
            foh.extend(day_foh)
            boh.extend(day_boh)
            tips.extend(day_tips)

        boh_ids = set()
        for r in boh:
            boh_ids.add(r["emp_id"])

        # Collect per-position-row hours for each employee
        # Key: emp_id -> list of {position, hours, wage, otm, fixed_wk}
        ed = {}
        for r in foh + boh:
            eid = r["emp_id"]
            if eid not in ed:
                ed[eid] = {"name": r["employee_name"],
                           "dept": "BOH" if eid in boh_ids else "FOH",
                           "rows": [], "tips": 0.0}
            pos_name = r.get("position", "")
            pos = self.pos_by_name(pos_name)
            wage = safe_float(pos.get("hourly_wage", 0)) if pos else 0.0
            otm = safe_float(pos.get("overtime_rate", 1.5)) if pos else 1.5
            fw = None
            if pos:
                fwv = pos.get("fixed_weekly_wage")
                if fwv and safe_float(fwv) > 0:
                    fw = safe_float(fwv)
            hrs = safe_float(r.get("hours", 0))
            ed[eid]["rows"].append({
                "position": pos_name, "hours": hrs,
                "wage": wage, "otm": otm, "fixed_wk": fw,
            })
            if r in boh:
                ed[eid]["dept"] = "BOH"

        for r in tips:
            eid = r["emp_id"]
            if eid not in ed:
                ed[eid] = {"name": r["employee_name"], "dept": "FOH",
                           "rows": [], "tips": 0.0}
            ed[eid]["tips"] += safe_float(r.get("total_tip", 0))

        payroll = []
        for eid, d in ed.items():
            if not d["rows"] and d["tips"] == 0:
                continue

            # Aggregate hours per position
            pos_agg = {}
            for pr in d["rows"]:
                pn = pr["position"]
                if pn not in pos_agg:
                    pos_agg[pn] = {"hours": 0.0, "wage": pr["wage"],
                                   "otm": pr["otm"], "fixed_wk": pr["fixed_wk"]}
                pos_agg[pn]["hours"] += pr["hours"]

            total_hours = sum(pa["hours"] for pa in pos_agg.values())

            # Check for any fixed weekly wage
            has_fixed = any(pa["fixed_wk"] is not None for pa in pos_agg.values())

            reg_wages = 0.0
            ot_wages = 0.0
            breakdown_parts = []

            if has_fixed:
                # Fixed wage: use first fixed position's wage
                for pn, pa in pos_agg.items():
                    if pa["fixed_wk"]:
                        reg_wages = pa["fixed_wk"]
                        breakdown_parts.append(f"{pn} fixed ${pa['fixed_wk']:.0f}/wk")
                        break
            else:
                # Per-position wage calculation
                reg_hours_left = min(total_hours, 40)
                ot_hours_left = max(total_hours - 40, 0)

                # Distribute regular and OT hours proportionally per position
                for pn, pa in pos_agg.items():
                    ph = pa["hours"]
                    if total_hours > 0:
                        proportion = ph / total_hours
                    else:
                        proportion = 0
                    pos_reg = min(ph, reg_hours_left) if total_hours <= 40 else round(40 * proportion, 4)
                    pos_ot = ph - pos_reg if total_hours > 40 else 0.0

                    rw = round(pos_reg * pa["wage"], 2)
                    ow = round(pos_ot * pa["wage"] * pa["otm"], 2)
                    reg_wages += rw
                    ot_wages += ow
                    breakdown_parts.append(f"{pn} {ph:.1f}hrs @ {fmt(pa['wage'])}")

            tp = round(d["tips"], 2)
            positions_str = ", ".join(sorted(pos_agg.keys())) if pos_agg else ""
            wage_note = " + ".join(breakdown_parts) if len(pos_agg) > 1 else ""

            reg_h = min(total_hours, 40)
            ot_h = max(total_hours - 40, 0)

            payroll.append({
                "emp_id": eid, "employee_name": d["name"],
                "positions": positions_str,
                "department": d["dept"],
                "regular_hours": round(reg_h, 2),
                "overtime_hours": round(ot_h, 2),
                "hourly_rate": "split" if len(pos_agg) > 1 else (
                    list(pos_agg.values())[0]["wage"] if pos_agg else 0),
                "regular_wages": round(reg_wages, 2),
                "overtime_wages": round(ot_wages, 2),
                "total_tips": tp,
                "total_compensation": round(reg_wages + ot_wages + tp, 2),
                "wage_note": wage_note,
            })
        payroll.sort(key=lambda r: (r["department"], r["employee_name"]))
        return payroll

    def emp_weekly_profile(self, mon, emp_id):
        """Gather full weekly activity for a single employee."""
        # Load all days from Firebase/local via load_day (not raw CSV)
        foh = []
        boh = []
        tips = []
        for day_name in DAYS:
            day_foh, day_boh, day_tips = self.load_day(mon, day_name)
            foh.extend(day_foh)
            boh.extend(day_boh)
            tips.extend(day_tips)

        # Hours rows for this employee
        hours_rows = [r for r in foh + boh if r.get("emp_id") == emp_id]
        tip_rows = [r for r in tips if r.get("emp_id") == emp_id]

        # Build per-day breakdown
        day_data = {}  # day_name -> list of entry dicts
        for r in hours_rows:
            day = r.get("day", "")
            pos_name = r.get("position", "")
            wage = self.get_wage(pos_name)
            hrs = safe_float(r.get("hours", 0))
            entry = {
                "day": day, "shift": r.get("shift", "Dinner"),
                "position": pos_name, "hours": hrs,
                "hourly_wage": wage, "wages": round(hrs * wage, 2),
                "floor_tip": 0.0, "bar_tip": 0.0, "total_tip": 0.0,
            }
            day_data.setdefault(day, []).append(entry)

        # Merge tips into day_data entries
        for t in tip_rows:
            day = t.get("day", "")
            shift = t.get("shift", "Dinner")
            ft = safe_float(t.get("floor_tip", 0))
            bt = safe_float(t.get("bar_tip", 0))
            tt = safe_float(t.get("total_tip", 0))
            # Try to attach to matching hours entry
            matched = False
            for entry in day_data.get(day, []):
                if entry["shift"] == shift:
                    entry["floor_tip"] += ft
                    entry["bar_tip"] += bt
                    entry["total_tip"] += tt
                    matched = True
                    break
            if not matched:
                # Tip-only entry (no hours logged for this shift)
                day_data.setdefault(day, []).append({
                    "day": day, "shift": shift,
                    "position": t.get("position", ""),
                    "hours": 0, "hourly_wage": 0, "wages": 0,
                    "floor_tip": ft, "bar_tip": bt, "total_tip": tt,
                })

        # Compute totals
        total_hours = sum(e["hours"] for entries in day_data.values() for e in entries)
        total_wages = sum(e["wages"] for entries in day_data.values() for e in entries)
        total_floor = sum(e["floor_tip"] for entries in day_data.values() for e in entries)
        total_bar = sum(e["bar_tip"] for entries in day_data.values() for e in entries)
        total_tips = round(total_floor + total_bar, 2)
        days_worked = len([d for d, entries in day_data.items()
                           if any(e["hours"] > 0 for e in entries)])

        return {
            "days_worked": days_worked,
            "total_hours": round(total_hours, 2),
            "total_wages": round(total_wages, 2),
            "total_tips": total_tips,
            "total_floor": round(total_floor, 2),
            "total_bar": round(total_bar, 2),
            "total_compensation": round(total_wages + total_tips, 2),
            "day_data": day_data,
        }

    def export_payroll(self, mon, rows):
        p = self.ensure_wk(mon) / "payroll.csv"
        flds = ["emp_id", "employee_name", "positions", "department",
                "regular_hours", "overtime_hours", "hourly_rate",
                "regular_wages", "overtime_wages", "total_tips",
                "total_compensation", "wage_note"]
        self.write_csv(p, flds, rows)
        return p


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════════
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.configure(bg=BG_PAGE)
        self.minsize(MIN_W, MIN_H)
        self.geometry("1160x820")

        self.dm = DataManager(firebase_uid=getattr(self, '_logged_in_uid', None))
        self.toast = Toast(self)
        self.sel_date = date.today()
        self.cur_mon = monday_of(self.sel_date)
        self.dm.ensure_wk(self.cur_mon)
        self._screen = None

        if IS_MAC:
            self.bind_all("<MouseWheel>", self._global_wheel)
        else:
            self.bind_all("<MouseWheel>", self._global_wheel)
            self.bind_all("<Button-4>", self._global_wheel_linux)
            self.bind_all("<Button-5>", self._global_wheel_linux)

        self._build_nav()
        self.main = tk.Frame(self, bg=BG_PAGE)
        self.main.pack(fill="both", expand=True)
        self.nav_click("Today")

    def _global_wheel(self, event):
        w = event.widget
        while w:
            if isinstance(w, tk.Canvas):
                try:
                    if IS_MAC:
                        w.yview_scroll(int(-event.delta), "units")
                    else:
                        w.yview_scroll(int(-event.delta / 120), "units")
                except Exception:
                    pass
                return
            w = getattr(w, "master", None)

    def _global_wheel_linux(self, event):
        w = event.widget
        while w:
            if isinstance(w, tk.Canvas):
                try:
                    w.yview_scroll(-3 if event.num == 4 else 3, "units")
                except Exception:
                    pass
                return
            w = getattr(w, "master", None)

    # ══════════════════════════════════════════════════════════════════════
    #  NAVIGATION BAR
    # ══════════════════════════════════════════════════════════════════════
    def _build_nav(self):
        nav = tk.Frame(self, bg=BG_NAV, height=52)
        nav.pack(side="top", fill="x")
        nav.pack_propagate(False)

        tk.Label(nav, text="  Stamhad Payroll", bg=BG_NAV, fg="#7EB8FF",
                 font=(FONT, 16, "bold")).pack(side="left", padx=(10, 24))

        self.nav_btns = {}
        for lbl in ["Today", "Week View", "Employees", "Positions", "Payroll Report"]:
            b = tk.Label(nav, text=lbl, bg=BG_NAV, fg="#94A3B8",
                         font=(FONT, 11, "bold"), padx=14, pady=6, cursor="hand2")
            b.pack(side="left", padx=2, pady=8)
            b.bind("<Button-1>", lambda e, l=lbl: self.nav_click(l))
            b.bind("<Enter>", lambda e, w=b: w.config(bg="#2D4A7A") if w.cget("bg") != "#4F46E5" else None)
            b.bind("<Leave>", lambda e, w=b: w.config(bg=BG_NAV) if w.cget("bg") != "#4F46E5" else None)
            self.nav_btns[lbl] = b

        df = tk.Frame(nav, bg=BG_NAV)
        df.pack(side="right", padx=16)
        prev_lbl = tk.Label(df, text="\u25C0", bg=BG_NAV, fg="#B0C4DE",
                            font=(FONT, 14), cursor="hand2")
        prev_lbl.pack(side="left")
        prev_lbl.bind("<Button-1>", lambda e: self._prev_day())
        self.date_lbl = tk.Label(df, text="", bg=BG_NAV, fg="#FFD580",
                                 font=(FONT, 12, "bold"))
        self.date_lbl.pack(side="left", padx=10)
        next_lbl = tk.Label(df, text="\u25B6", bg=BG_NAV, fg="#B0C4DE",
                            font=(FONT, 14), cursor="hand2")
        next_lbl.pack(side="left")
        next_lbl.bind("<Button-1>", lambda e: self._next_day())
        self._upd_date()

    def _upd_date(self):
        self.date_lbl.config(text=self.sel_date.strftime("%A, %b %d %Y"))

    def _prev_day(self):
        self.sel_date -= timedelta(days=1)
        self.cur_mon = monday_of(self.sel_date)
        self._upd_date()
        if self._screen == "Today":
            self.nav_click("Today")

    def _next_day(self):
        self.sel_date += timedelta(days=1)
        self.cur_mon = monday_of(self.sel_date)
        self._upd_date()
        if self._screen == "Today":
            self.nav_click("Today")

    def nav_click(self, lbl):
        for n, b in self.nav_btns.items():
            b.config(bg="#4F46E5" if n == lbl else BG_NAV,
                     fg="#FFFFFF" if n == lbl else "#94A3B8")
        self._screen = lbl
        for w in self.main.winfo_children():
            w.destroy()
        {"Today": self.pg_today, "Week View": self.pg_week,
         "Employees": self.pg_emps, "Positions": self.pg_pos,
         "Payroll Report": self.pg_payroll}[lbl]()

    def _clr(self):
        for w in self.main.winfo_children():
            w.destroy()

    # ══════════════════════════════════════════════════════════════════════
    #  POSITIONS PAGE — click row to edit, FOH/BOH dropdown in dialog
    # ══════════════════════════════════════════════════════════════════════
    def pg_pos(self):
        scroll = ScrollFrame(self.main, bg=BG_PAGE)
        scroll.pack(fill="both", expand=True)

        hdr = tk.Frame(scroll, bg=BG_PAGE)
        hdr.pack(fill="x", padx=24, pady=(18, 10))
        tk.Label(hdr, text="Position Management", bg=BG_PAGE, fg=FG,
                 font=(FONT, 18, "bold")).pack(side="left")
        Btn(hdr, text="+  Add Position", command=self._pos_dlg,
            style="success").pack(side="right")

        if not self.dm.positions:
            empty = Card(scroll)
            empty.pack(fill="x", padx=24, pady=20)
            tk.Label(empty, text="No positions yet \u2014 click 'Add Position' to get started.",
                     bg=BG_CARD, fg=FG_SEC, font=(FONT, 13)).pack(pady=20)
            return

        card = Card(scroll)
        card.pack(fill="x", padx=24, pady=4)

        cols = ("Name", "Dept", "Hourly", "Fixed Wk", "OT", "Tip Pts",
                "Bar Share %", "Bar Tips?", "")
        for j, c in enumerate(cols):
            tk.Label(card, text=c, bg=BG_CARD, fg=FG_HDR, font=(FONT, 11, "bold"),
                     anchor="w", padx=8, pady=8).grid(row=0, column=j, sticky="we")
        tk.Frame(card, bg=BORDER, height=1).grid(row=1, column=0, columnspan=len(cols), sticky="we")

        for i, pos in enumerate(self.dm.positions):
            row_num = i + 2
            bg = ROW_B if i % 2 else ROW_A
            vals = [
                pos["name"],
                pos.get("department", ""),
                fmt(pos.get("hourly_wage", 0)),
                fmt(pos.get("fixed_weekly_wage", 0)) if pos.get("fixed_weekly_wage") else "\u2014",
                f'{safe_float(pos.get("overtime_rate", 1.5)):.1f}x',
                str(int(safe_float(pos.get("tip_points", 0)))),
                f'{safe_float(pos.get("bar_tip_share_pct", 0)):.0f}%',
                "Yes" if pos.get("receives_bar_tips") else "No",
            ]
            for j, v in enumerate(vals):
                cell = tk.Frame(card, bg=bg, cursor="hand2")
                cell.grid(row=row_num, column=j, sticky="nswe")
                cell.bind("<Button-1>", lambda e, p=pos: self._pos_dlg(p))
                if j == 1:
                    pill = DeptPill(cell, v)
                    pill.pack(side="left", padx=8, pady=6)
                    pill.bind("<Button-1>", lambda e, p=pos: self._pos_dlg(p))
                else:
                    lbl = tk.Label(cell, text=v, bg=bg, fg=FG, font=(FONT, 12),
                                   anchor="w", padx=8, pady=6, cursor="hand2")
                    lbl.pack(side="left")
                    lbl.bind("<Button-1>", lambda e, p=pos: self._pos_dlg(p))

            acell = tk.Frame(card, bg=bg)
            acell.grid(row=row_num, column=len(cols) - 1, sticky="we")
            edit_lbl = tk.Label(acell, text="\u270F\uFE0F", bg=bg, fg=ACCENT,
                                font=(FONT, 14), cursor="hand2", padx=4)
            edit_lbl.pack(side="left", padx=2, pady=4)
            edit_lbl.bind("<Button-1>", lambda e, p=pos: self._pos_dlg(p))
            Btn(acell, text="\U0001F5D1", style="danger",
                command=lambda p=pos: self._del_pos(p)).pack(side="left", padx=3, pady=4)

    def _pos_dlg(self, pos=None):
        win = tk.Toplevel(self)
        win.title("Edit Position" if pos else "New Position")
        win.configure(bg=BG_CARD)
        win.geometry("460x600")
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="Edit Position" if pos else "New Position",
                 bg=BG_CARD, fg=ACCENT, font=(FONT, 16, "bold")).pack(pady=(20, 14))

        fields = {}
        # Name field
        tk.Label(win, text="Position Name", bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 11), anchor="w").pack(fill="x", padx=28)
        name_e = Inp(win, width=28)
        name_e.pack(fill="x", padx=28, pady=(0, 8))
        if pos:
            name_e.insert(0, pos.get("name", ""))
        fields["name"] = name_e

        # Department DROPDOWN
        tk.Label(win, text="Department", bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 11), anchor="w").pack(fill="x", padx=28)
        dept_var = tk.StringVar(value=DEPT_DISPLAY.get(pos.get("department", "FOH"), DEPT_OPTIONS[0]) if pos else DEPT_OPTIONS[0])
        dept_cb = ttk.Combobox(win, textvariable=dept_var, values=DEPT_OPTIONS,
                               state="readonly", font=(FONT, 12), width=26)
        dept_cb.pack(fill="x", padx=28, pady=(0, 8))
        fields["department"] = dept_var

        # Other fields
        specs = [
            ("hourly_wage", "Hourly Wage ($)", "0"),
            ("fixed_weekly_wage", "Fixed Weekly Wage ($, blank = none)", ""),
            ("overtime_rate", "Overtime Multiplier", "1.5"),
            ("tip_points", "Tip Points (FOH only)", "0"),
            ("bar_tip_share_pct", "Bar Tip Share % (Barback)", "0"),
        ]
        for key, lbl, dflt in specs:
            tk.Label(win, text=lbl, bg=BG_CARD, fg=FG_SEC, font=(FONT, 11),
                     anchor="w").pack(fill="x", padx=28)
            e = Inp(win, width=28)
            e.pack(fill="x", padx=28, pady=(0, 8))
            v = str(pos.get(key, dflt)) if pos else dflt
            if v in ("None", ""):
                v = dflt
            e.insert(0, v)
            fields[key] = e

        bar_var = tk.BooleanVar(value=pos.get("receives_bar_tips", False) if pos else False)
        tk.Checkbutton(win, text="Receives Bar Tips (Bartender)", variable=bar_var,
                       bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                       activebackground=BG_CARD,
                       font=(FONT, 11)).pack(fill="x", padx=28, pady=8)

        btn_frame = tk.Frame(win, bg=BG_CARD)
        btn_frame.pack(pady=18)

        def save():
            nm = fields["name"].get().strip()
            dp_raw = fields["department"].get()
            dp = DEPT_MAP.get(dp_raw, "FOH")
            if not nm:
                messagebox.showwarning("Missing", "Name required.", parent=win)
                return

            is_edit = pos is not None
            if is_edit:
                old_wage = safe_float(pos.get("hourly_wage", 0))
                new_wage = safe_float(fields["hourly_wage"].get())
                if old_wage != new_wage:
                    if not messagebox.askyesno("Confirm Wage Change",
                            "Updating this wage will affect all employees in this position. Continue?",
                            parent=win):
                        return

            data = {
                "name": nm, "department": dp,
                "hourly_wage": safe_float(fields["hourly_wage"].get()),
                "fixed_weekly_wage": safe_float(fields["fixed_weekly_wage"].get()) or None,
                "overtime_rate": safe_float(fields["overtime_rate"].get(), 1.5),
                "tip_points": safe_float(fields["tip_points"].get()),
                "bar_tip_share_pct": safe_float(fields["bar_tip_share_pct"].get()),
                "receives_bar_tips": bar_var.get(),
            }
            if is_edit:
                idx = self.dm.positions.index(pos)
                self.dm.positions[idx] = data
            else:
                self.dm.positions.append(data)
            self.dm.save_pos()
            win.destroy()
            self._clr()
            self.pg_pos()
            self.toast.show("Position saved!")

        def cancel():
            win.destroy()

        Btn(btn_frame, text="\u2713  Save", command=save, style="primary").pack(side="left", padx=8)
        Btn(btn_frame, text="Cancel", command=cancel, style="cancel").pack(side="left", padx=8)

    def _del_pos(self, p):
        if messagebox.askyesno("Delete Position", f'Delete "{p["name"]}"?\nThis cannot be undone.'):
            self.dm.positions.remove(p)
            self.dm.save_pos()
            self._clr()
            self.pg_pos()
            self.toast.show("Position deleted.", bg=WARN_BG, fg=WARN_FG)

    # ══════════════════════════════════════════════════════════════════════
    #  EMPLOYEES PAGE
    # ══════════════════════════════════════════════════════════════════════
    def pg_emps(self):
        scroll = ScrollFrame(self.main, bg=BG_PAGE)
        scroll.pack(fill="both", expand=True)

        hdr = tk.Frame(scroll, bg=BG_PAGE)
        hdr.pack(fill="x", padx=24, pady=(18, 10))
        tk.Label(hdr, text="Employee Management", bg=BG_PAGE, fg=FG,
                 font=(FONT, 18, "bold")).pack(side="left")
        Btn(hdr, text="+  Add Employee", command=self._emp_dlg,
            style="success").pack(side="right")

        foh_list, boh_list = self.dm.sorted_employees()

        for dept_label, emp_list, color, dept_code in [
            ("Front of House", foh_list, ACCENT, "FOH"),
            ("Back of House", boh_list, "#E67E22", "BOH"),
        ]:
            SectionBar(scroll, dept_label, color=color, bg=BG_PAGE).pack(
                fill="x", padx=24, pady=(16, 6))
            card = Card(scroll)
            card.pack(fill="x", padx=24, pady=2)

            if not emp_list:
                tk.Label(card, text="No employees in this department.",
                         bg=BG_CARD, fg=FG_SEC, font=(FONT, 12)).pack(pady=10)
                continue

            for i, emp in enumerate(emp_list):
                bg = ROW_B if i % 2 else ROW_A
                row = tk.Frame(card, bg=bg)
                row.pack(fill="x")

                arrow_f = tk.Frame(row, bg=bg)
                arrow_f.pack(side="left", padx=(4, 0))
                if i > 0:
                    up_lbl = tk.Label(arrow_f, text="\u25B2", bg=bg, fg=FG_SEC,
                                      font=(FONT, 8), padx=2, cursor="hand2")
                    up_lbl.pack()
                    up_lbl.bind("<Button-1>", lambda e, em=emp: self._move_emp(em, -1))
                else:
                    tk.Label(arrow_f, text="\u25B2", bg=bg, fg="#D1D5DB",
                             font=(FONT, 8), padx=2).pack()
                if i < len(emp_list) - 1:
                    dn_lbl = tk.Label(arrow_f, text="\u25BC", bg=bg, fg=FG_SEC,
                                      font=(FONT, 8), padx=2, cursor="hand2")
                    dn_lbl.pack()
                    dn_lbl.bind("<Button-1>", lambda e, em=emp: self._move_emp(em, 1))
                else:
                    tk.Label(arrow_f, text="\u25BC", bg=bg, fg="#D1D5DB",
                             font=(FONT, 8), padx=2).pack()

                tk.Label(row, text=emp["id"], bg=bg, fg=FG_SEC, font=("Consolas", 11),
                         width=8, anchor="w", padx=8).pack(side="left", pady=6)

                name_lbl = tk.Label(row, text=emp["name"], bg=bg, fg=ACCENT,
                                    font=(FONT, 12, "bold"), width=22, anchor="w",
                                    padx=6, cursor="hand2")
                name_lbl.pack(side="left", pady=6)
                name_lbl.bind("<Button-1>", lambda e, emp_r=emp: self._open_emp_profile(emp_r))

                parts = []
                for a in emp.get("positions", []):
                    live_wage = self.dm.get_wage(a["position_name"])
                    parts.append(f'{a["position_name"]} ({fmt(live_wage)})')
                pos_lbl = tk.Label(row, text=", ".join(parts), bg=bg, fg=FG_SEC,
                                   font=(FONT, 11), anchor="w", padx=6, cursor="hand2")
                pos_lbl.pack(side="left", fill="x", expand=True, pady=6)
                pos_lbl.bind("<Button-1>", lambda e, emp_r=emp: self._open_emp_profile(emp_r))

                edit_lbl = tk.Label(row, text="\u270F\uFE0F", bg=bg, fg=ACCENT,
                                    font=(FONT, 14), cursor="hand2", padx=4)
                edit_lbl.pack(side="right", padx=2, pady=4)
                edit_lbl.bind("<Button-1>", lambda e, emp_r=emp: self._emp_dlg(emp_r))

                Btn(row, text="\U0001F5D1", style="danger",
                    command=lambda e=emp: self._del_emp(e)).pack(side="right", padx=3, pady=4)

    def _move_emp(self, emp, direction):
        self.dm.reorder_emp(emp, direction)
        self._clr()
        self.pg_emps()

    def _emp_dlg(self, emp=None):
        win = tk.Toplevel(self)
        win.title("Edit Employee" if emp else "New Employee")
        win.configure(bg=BG_CARD)
        win.geometry("520x600")
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="Edit Employee" if emp else "New Employee",
                 bg=BG_CARD, fg=ACCENT, font=(FONT, 16, "bold")).pack(pady=(20, 12))

        tk.Label(win, text="Full Name", bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 11)).pack(fill="x", padx=28)
        ne = Inp(win, width=30)
        ne.pack(fill="x", padx=28, pady=(0, 8))
        if emp:
            ne.insert(0, emp["name"])

        if emp:
            tk.Label(win, text=f"ID: {emp['id']}", bg=BG_CARD, fg=FG_SEC,
                     font=("Consolas", 11)).pack(padx=28, anchor="w")

        tk.Label(win, text="Assigned Positions (wages set in Position Management)",
                 bg=BG_CARD, fg=ACCENT, font=(FONT, 12, "bold")).pack(fill="x", padx=28, pady=(12, 6))

        pf = tk.Frame(win, bg=BG_CARD)
        pf.pack(fill="both", expand=True, padx=28)
        existing_names = set()
        if emp:
            existing_names = {a["position_name"] for a in emp.get("positions", [])}

        pvars = []
        for pos in self.dm.positions:
            f = tk.Frame(pf, bg=BG_CARD)
            f.pack(fill="x", pady=3)
            v = tk.BooleanVar(value=pos["name"] in existing_names)
            tk.Checkbutton(f, text=pos["name"], variable=v, bg=BG_CARD, fg=FG,
                           selectcolor=BG_INPUT, activebackground=BG_CARD,
                           font=(FONT, 12),
                           command=lambda: _update_main()).pack(side="left")
            DeptPill(f, pos.get("department", "FOH")).pack(side="left", padx=8)
            tk.Label(f, text=f'({fmt(pos.get("hourly_wage", 0))}/hr)',
                     bg=BG_CARD, fg=FG_SEC, font=(FONT, 11)).pack(side="left", padx=4)
            pvars.append((v, pos["name"]))

        # ── Main position selector ──────────────────────────────────────
        mp_frame = tk.Frame(win, bg=BG_CARD)
        mp_frame.pack(fill="x", padx=28, pady=(8, 4))
        tk.Label(mp_frame, text="Main Position", bg=BG_CARD, fg=ACCENT,
                 font=(FONT, 12, "bold")).pack(anchor="w")
        main_pos_cb = ttk.Combobox(mp_frame, state="readonly", width=25,
                                   font=(FONT, 11))
        main_pos_cb.pack(anchor="w", pady=(4, 0))
        cur_main = emp.get("main_position", "") if emp else ""

        def _update_main():
            checked = [pn for v, pn in pvars if v.get()]
            main_pos_cb["values"] = checked
            cur = main_pos_cb.get()
            if not checked:
                main_pos_cb.set("")
            elif len(checked) == 1:
                main_pos_cb.set(checked[0])
            elif cur not in checked:
                main_pos_cb.set(checked[0])

        _update_main()
        if cur_main and cur_main in [pn for v, pn in pvars if v.get()]:
            main_pos_cb.set(cur_main)
        elif main_pos_cb["values"]:
            main_pos_cb.set(main_pos_cb["values"][0] if main_pos_cb["values"] else "")

        btn_frame = tk.Frame(win, bg=BG_CARD)
        btn_frame.pack(pady=18)

        def save():
            name = ne.get().strip()
            if not name:
                messagebox.showwarning("Missing", "Name required.", parent=win)
                return
            assigned = [{"position_name": pn} for v, pn in pvars if v.get()]
            if not assigned:
                messagebox.showwarning("Missing", "Assign at least one position.", parent=win)
                return
            mp = main_pos_cb.get().strip()
            if not mp and assigned:
                mp = assigned[0]["position_name"]
            if emp:
                emp["name"] = name
                emp["positions"] = assigned
                emp["main_position"] = mp
            else:
                self.dm.employees.append({"id": gen_id(), "name": name,
                                          "positions": assigned, "main_position": mp,
                                          "sort_order": 9999})
            self.dm.save_emp()
            win.destroy()
            self._clr()
            self.pg_emps()
            self.toast.show("Employee saved!")

        def cancel():
            win.destroy()

        Btn(btn_frame, text="\u2713  Save", command=save, style="primary").pack(side="left", padx=8)
        Btn(btn_frame, text="Cancel", command=cancel, style="cancel").pack(side="left", padx=8)

    def _del_emp(self, emp):
        if messagebox.askyesno("Delete Employee", f'Delete "{emp["name"]}"?\nThis cannot be undone.'):
            self.dm.employees.remove(emp)
            self.dm.save_emp()
            self._clr()
            self.pg_emps()
            self.toast.show("Employee deleted.", bg=WARN_BG, fg=WARN_FG)

    # ══════════════════════════════════════════════════════════════════════
    #  TODAY — TAB ORDER: Employees | Hours | Tips + Footer
    # ══════════════════════════════════════════════════════════════════════
    def pg_today(self):
        self.dm.ensure_wk(self.cur_mon)
        day_name = DAYS[self.sel_date.weekday()]

        foh_saved, boh_saved, tip_saved = self.dm.load_day(self.cur_mon, day_name)
        saved_blocks = []
        for r in foh_saved + boh_saved:
            saved_blocks.append({
                "emp_id": r["emp_id"], "position_name": r["position"],
                "shift": r.get("shift", "Dinner"), "hours": safe_float(r.get("hours", 0)),
            })

        self._saved_by_emp = {}
        for b in saved_blocks:
            self._saved_by_emp.setdefault(b["emp_id"], []).append(b)

        self._checked_emp_ids = set(self._saved_by_emp.keys())

        self._hours_data = []
        for b in saved_blocks:
            emp = self.dm.emp_by_id(b["emp_id"])
            self._hours_data.append({
                "emp_id": b["emp_id"],
                "emp_name": emp["name"] if emp else "",
                "position_name": b["position_name"],
                "shift": b.get("shift", "Dinner"),
                "hours": b.get("hours", 0),
            })

        self._saved_tip_totals = {}
        for r in tip_saved:
            sh = r.get("shift", "Dinner")
            if sh not in self._saved_tip_totals:
                self._saved_tip_totals[sh] = {"floor": 0.0, "bar": 0.0}
            self._saved_tip_totals[sh]["floor"] += safe_float(r.get("floor_tip", 0))
            self._saved_tip_totals[sh]["bar"] += safe_float(r.get("bar_tip", 0))

        self._has_saved = len(saved_blocks) > 0
        self._day_tips = {}
        self._tip_entry_values = {}  # reset on new day load

        content = tk.Frame(self.main, bg=BG_PAGE)
        content.pack(fill="both", expand=True)

        if self._has_saved:
            banner = tk.Frame(content, bg=WARN_BG, highlightbackground=WARN_BORD,
                              highlightthickness=0)
            banner.pack(fill="x", padx=16, pady=(8, 0))
            tk.Frame(banner, bg=WARN_BORD, width=4).pack(side="left", fill="y")
            tk.Label(banner,
                     text=f"  Editing saved entry for {self.sel_date.strftime('%A, %b %d')}",
                     bg=WARN_BG, fg=WARN_FG, font=(FONT, 12, "bold"),
                     pady=8).pack(side="left", padx=8)
        elif self.sel_date != date.today():
            banner = tk.Frame(content, bg=WARN_BG, highlightbackground=WARN_BORD,
                              highlightthickness=0)
            banner.pack(fill="x", padx=16, pady=(8, 0))
            tk.Frame(banner, bg=WARN_BORD, width=4).pack(side="left", fill="y")
            tk.Label(banner,
                     text=f"  Editing past entry: {self.sel_date.strftime('%A, %b %d %Y')}",
                     bg=WARN_BG, fg=WARN_FG, font=(FONT, 12, "bold"),
                     pady=8).pack(side="left", padx=8)

        # TAB ORDER FIX: Employees -> Hours -> Tips
        tab_bar = tk.Frame(content, bg=BG_PAGE)
        tab_bar.pack(fill="x", padx=16, pady=(10, 0))

        self._day_tab_btns = {}
        self._tab_content = tk.Frame(content, bg=BG_PAGE)
        self._tab_content.pack(fill="both", expand=True)

        for t in ["\U0001F465 Employees", "\u23F1 Hours", "\U0001F4B0 Tips"]:
            b = tk.Label(tab_bar, text=f"  {t}  ", bg="#FFFFFF", fg="#374151",
                         font=(FONT, 11, "bold"), padx=16, pady=8,
                         cursor="hand2", relief="solid", bd=1)
            b.pack(side="left", padx=4)
            b.bind("<Button-1>", lambda e, t2=t: self._day_tab(t2))
            self._day_tab_btns[t] = b

        footer = tk.Frame(self.main, bg=BG_CARD, highlightbackground=BORDER,
                          highlightthickness=1)
        footer.pack(side="bottom", fill="x")

        self._footer_info = tk.Label(footer, text="", bg=BG_CARD, fg=FG_SEC,
                                      font=(FONT, 11))
        self._footer_info.pack(side="left", padx=16, pady=10)

        Btn(footer, text="\u2713  Save Day", style="primary",
            command=self._save_day).pack(side="right", padx=16, pady=8)

        self._day_tab("\U0001F465 Employees")

    def _day_tab(self, name):
        self._snapshot_hours_from_widgets()
        self._snapshot_tips_from_widgets()

        for n, b in self._day_tab_btns.items():
            if n == name:
                b.config(bg=ACCENT, fg="#FFFFFF")
            else:
                b.config(bg="#FFFFFF", fg="#374151")
        for w in self._tab_content.winfo_children():
            w.destroy()

        if name == "\U0001F465 Employees":
            self._build_tab_employees()
        elif name == "\u23F1 Hours":
            self._build_tab_hours()
        elif name == "\U0001F4B0 Tips":
            self._build_tab_tips()

        self._update_footer()

    def _snapshot_hours_from_widgets(self):
        if not hasattr(self, "_hours_widgets"):
            return
        new_data = []
        for hw in self._hours_widgets:
            try:
                new_data.append({
                    "emp_id": hw["emp_id"], "emp_name": hw["emp_name"],
                    "position_name": hw["pos_var"].get(),
                    "shift": hw["shift_var"].get() or "Dinner",
                    "hours": safe_float(hw["hours_entry"].get()),
                })
            except Exception:
                pass
        if new_data:
            self._hours_data = new_data
        self._hours_widgets = []

    def _snapshot_checked_from_widgets(self):
        if not hasattr(self, "_check_vars"):
            return
        new_checked = set()
        for eid, var in self._check_vars.items():
            try:
                if var.get():
                    new_checked.add(eid)
            except Exception:
                pass
        self._checked_emp_ids = new_checked

    def _snapshot_tips_from_widgets(self):
        """Capture tip entry values before destroying the Tips tab widgets."""
        if not hasattr(self, "_shift_tip_entries"):
            return
        if not self._shift_tip_entries:
            return
        if not hasattr(self, "_tip_entry_values"):
            self._tip_entry_values = {}
        for shift, entries in self._shift_tip_entries.items():
            try:
                fl = safe_float(entries["floor"].get())
                br = safe_float(entries["bar"].get())
                self._tip_entry_values[shift] = {"floor": fl, "bar": br}
            except Exception:
                pass

    def _gather_blocks(self):
        self._snapshot_hours_from_widgets()
        return list(self._hours_data)

    def _update_footer(self):
        blocks = self._hours_data if hasattr(self, "_hours_data") else []
        n_emp = len(set(b["emp_id"] for b in blocks))
        tip_total = 0.0
        for td in getattr(self, "_day_tips", {}).values():
            tip_total += safe_float(td.get("floor_tips", 0))
            tip_total += safe_float(td.get("bar_tips", 0))
        if hasattr(self, "_footer_info"):
            self._footer_info.config(
                text=f"Employees: {n_emp}    |    Tip Input Total: {fmt(tip_total)}")

    # ── TAB 1: Employees — SIMPLIFIED CHECKLIST ────────────────────────
    def _build_tab_employees(self):
        scroll = ScrollFrame(self._tab_content, bg=BG_PAGE)
        scroll.pack(fill="both", expand=True)

        hdr = tk.Frame(scroll, bg=BG_PAGE)
        hdr.pack(fill="x", padx=24, pady=(10, 6))
        day_name = DAYS[self.sel_date.weekday()]
        tk.Label(hdr, text=f"Who Worked {day_name}?", bg=BG_PAGE, fg=FG,
                 font=(FONT, 16, "bold")).pack(side="left")

        btn_row = tk.Frame(scroll, bg=BG_PAGE)
        btn_row.pack(fill="x", padx=24, pady=4)
        Btn(btn_row, text="Select All", style="ghost",
            command=lambda: self._toggle_all(True)).pack(side="left", padx=4)
        Btn(btn_row, text="Clear All", style="ghost",
            command=lambda: self._toggle_all(False)).pack(side="left", padx=4)

        self._check_vars = {}
        foh_list, boh_list = self.dm.sorted_employees()

        for dept_label, emp_list, color in [
            ("Front of House", foh_list, ACCENT),
            ("Back of House", boh_list, "#E67E22"),
        ]:
            SectionBar(scroll, dept_label, color=color, bg=BG_PAGE).pack(
                fill="x", padx=24, pady=(12, 4))

            if not emp_list:
                tk.Label(scroll, text="No employees in this department.",
                         bg=BG_PAGE, fg=FG_SEC, font=(FONT, 12)).pack(
                    anchor="w", padx=28, pady=4)
                continue

            for emp in emp_list:
                eid = emp["id"]
                dept = self.dm.emp_dept(emp)

                row_frame = tk.Frame(scroll, bg=BG_CARD, highlightbackground=BORDER_LT,
                                     highlightthickness=1)
                row_frame.pack(fill="x", padx=24, pady=1)

                var = tk.BooleanVar(value=eid in self._checked_emp_ids)
                cb = tk.Checkbutton(row_frame, text=emp["name"], variable=var,
                                    bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                                    activebackground=BG_CARD,
                                    font=(FONT, 12, "bold"),
                                    command=lambda v=var, e=emp: self._on_emp_check(v, e))
                cb.pack(side="left", padx=(8, 4), pady=8)
                DeptPill(row_frame, dept).pack(side="left", padx=4)

                self._check_vars[eid] = var

    def _on_emp_check(self, var, emp):
        eid = emp["id"]
        if var.get():
            self._checked_emp_ids.add(eid)
            has_rows = any(h["emp_id"] == eid for h in self._hours_data)
            if not has_rows:
                pos_names = [a["position_name"] for a in emp.get("positions", [])]
                main_pos = emp.get("main_position", "")
                default_pos = main_pos if main_pos and main_pos in pos_names else (pos_names[0] if pos_names else "")
                self._hours_data.append({
                    "emp_id": eid, "emp_name": emp["name"],
                    "position_name": default_pos, "shift": "Dinner", "hours": 0,
                })
        else:
            self._checked_emp_ids.discard(eid)
            self._hours_data = [h for h in self._hours_data if h["emp_id"] != eid]
        self._update_footer()

    def _toggle_all(self, val):
        for eid, var in self._check_vars.items():
            was = var.get()
            var.set(val)
            if val and not was:
                emp = self.dm.emp_by_id(eid)
                if emp:
                    self._on_emp_check(var, emp)
            elif not val and was:
                self._checked_emp_ids.discard(eid)
                self._hours_data = [h for h in self._hours_data if h["emp_id"] != eid]
        self._update_footer()

    # ── TAB 2: Hours — position/shift/hours management ─────────────────
    def _build_tab_hours(self):
        scroll = ScrollFrame(self._tab_content, bg=BG_PAGE)
        scroll.pack(fill="both", expand=True)

        day_name = DAYS[self.sel_date.weekday()]

        hdr = tk.Frame(scroll, bg=BG_PAGE)
        hdr.pack(fill="x", padx=24, pady=(10, 6))
        tk.Label(hdr, text=f"Hours Entry \u2014 {day_name}", bg=BG_PAGE, fg=FG,
                 font=(FONT, 16, "bold")).pack(side="left")

        checked = self._checked_emp_ids
        if not checked:
            card = Card(scroll)
            card.pack(fill="x", padx=24, pady=20)
            tk.Label(card, text="No employees checked in the Employees tab.",
                     bg=BG_CARD, fg=FG_SEC, font=(FONT, 13)).pack(pady=16)
            self._hours_widgets = []
            return

        has_zero = any(h["hours"] == 0 for h in self._hours_data if h["emp_id"] in checked)
        if has_zero:
            warn = tk.Frame(scroll, bg=WARN_BG, highlightbackground=WARN_BORD,
                            highlightthickness=0)
            warn.pack(fill="x", padx=24, pady=(0, 8))
            tk.Frame(warn, bg=WARN_BORD, width=4).pack(side="left", fill="y")
            tk.Label(warn, text="  Some shifts have no hours entered yet",
                     bg=WARN_BG, fg=WARN_FG, font=(FONT, 11, "bold"),
                     pady=8).pack(side="left", padx=8)

        self._hours_widgets = []

        foh_list, boh_list = self.dm.sorted_employees()
        foh_checked = [e for e in foh_list if e["id"] in checked]
        boh_checked = [e for e in boh_list if e["id"] in checked]

        for dept_label, emp_list, color in [
            ("Front of House", foh_checked, ACCENT),
            ("Back of House", boh_checked, "#E67E22"),
        ]:
            if not emp_list:
                continue
            SectionBar(scroll, dept_label, color=color, bg=BG_PAGE).pack(
                fill="x", padx=24, pady=(12, 4))

            for emp in emp_list:
                eid = emp["id"]
                emp_rows = [h for h in self._hours_data if h["emp_id"] == eid]

                emp_card = Card(scroll)
                emp_card.pack(fill="x", padx=24, pady=2)

                name_bar = tk.Frame(emp_card, bg=BG_CARD)
                name_bar.pack(fill="x")
                hrs_name_lbl = tk.Label(name_bar, text=emp["name"], bg=BG_CARD,
                                        fg=ACCENT, font=(FONT, 13, "bold"),
                                        cursor="hand2")
                hrs_name_lbl.pack(side="left")
                hrs_name_lbl.bind("<Button-1>", lambda e, em=emp: self._open_emp_profile(em))
                DeptPill(name_bar, self.dm.emp_dept(emp)).pack(side="left", padx=8)

                rows_frame = tk.Frame(emp_card, bg=BG_CARD)
                rows_frame.pack(fill="x", padx=(8, 0), pady=(4, 0))

                if not emp_rows:
                    pos_names = [a["position_name"] for a in emp.get("positions", [])]
                    main_pos = emp.get("main_position", "")
                    default_pos = main_pos if main_pos and main_pos in pos_names else (pos_names[0] if pos_names else "")
                    emp_rows = [{"emp_id": eid, "emp_name": emp["name"],
                                 "position_name": default_pos, "shift": "Dinner", "hours": 0}]
                    self._hours_data.extend(emp_rows)

                for row_data in emp_rows:
                    self._add_hours_row_widget(rows_frame, emp, row_data)

                Btn(rows_frame, text="+  Add Shift", style="success",
                    command=lambda rf=rows_frame, e=emp: self._add_new_hours_row(rf, e)).pack(
                    anchor="w", pady=4)

    def _add_hours_row_widget(self, parent, emp, row_data):
        bf = tk.Frame(parent, bg=BG_CARD)
        bf.pack(fill="x", pady=2)

        pos_names = [a["position_name"] for a in emp.get("positions", [])]
        pcb = ttk.Combobox(bf, values=pos_names, width=14, state="readonly",
                           font=(FONT, 11))
        pcb.set(row_data.get("position_name", pos_names[0] if pos_names else ""))
        pcb.pack(side="left", padx=(0, 8))

        tk.Label(bf, text="Shift:", bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 11)).pack(side="left")
        scb = ttk.Combobox(bf, values=SHIFTS, width=9, state="readonly",
                           font=(FONT, 11))
        scb.set(row_data.get("shift", "Dinner"))
        scb.pack(side="left", padx=(4, 8))

        tk.Label(bf, text="Hrs:", bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 11)).pack(side="left")
        he = Inp(bf, width=6)
        he.pack(side="left", padx=(4, 8))
        hrs_val = row_data.get("hours", 0)
        if hrs_val:
            he.insert(0, str(hrs_val))

        hw = {
            "emp_id": emp["id"], "emp_name": emp["name"],
            "pos_var": pcb, "shift_var": scb, "hours_entry": he,
            "frame": bf, "row_data": row_data,
        }
        self._hours_widgets.append(hw)

        def remove():
            self._hours_widgets.remove(hw)
            if row_data in self._hours_data:
                self._hours_data.remove(row_data)
            bf.destroy()
        Btn(bf, text="\u2715", style="danger", command=remove).pack(side="left", padx=4)

    def _add_new_hours_row(self, parent, emp):
        pos_names = [a["position_name"] for a in emp.get("positions", [])]
        main_pos = emp.get("main_position", "")
        default_pos = main_pos if main_pos and main_pos in pos_names else (pos_names[0] if pos_names else "")
        new_data = {
            "emp_id": emp["id"], "emp_name": emp["name"],
            "position_name": default_pos,
            "shift": "Dinner", "hours": 0,
        }
        self._hours_data.append(new_data)
        self._add_hours_row_widget(parent, emp, new_data)
        children = parent.winfo_children()
        for child in children:
            if isinstance(child, Btn):
                try:
                    if "Add" in child.cget("text") or "+" in child.cget("text"):
                        child.pack_forget()
                        child.pack(anchor="w", pady=4)
                except Exception:
                    pass

    # ── TAB 3: Tips (only shows shifts with hours) ─────────────────────
    def _build_tab_tips(self):
        scroll = ScrollFrame(self._tab_content, bg=BG_PAGE)
        scroll.pack(fill="both", expand=True)

        blocks = self._hours_data
        day_name = DAYS[self.sel_date.weekday()]

        hdr = tk.Frame(scroll, bg=BG_PAGE)
        hdr.pack(fill="x", padx=24, pady=(10, 6))
        tk.Label(hdr, text=f"Tip Entry \u2014 {day_name}", bg=BG_PAGE, fg=FG,
                 font=(FONT, 16, "bold")).pack(side="left")

        # Only show shifts that have at least one employee with hours
        foh_by_shift = {}
        for b in blocks:
            pos = self.dm.pos_by_name(b["position_name"])
            if pos and pos.get("department") == "FOH" and safe_float(b.get("hours", 0)) > 0:
                foh_by_shift.setdefault(b["shift"], []).append(b)

        if not foh_by_shift:
            card = Card(scroll)
            card.pack(fill="x", padx=24, pady=20)
            tk.Label(card, text="No FOH employees with hours entered in the Hours tab.",
                     bg=BG_CARD, fg=FG_SEC, font=(FONT, 13)).pack(pady=16)
            return

        self._shift_tip_entries = {}
        self._shift_tip_display = {}

        for shift in SHIFTS:
            if shift not in foh_by_shift:
                continue

            shift_hdr = tk.Frame(scroll, bg=BG_PAGE)
            shift_hdr.pack(fill="x", padx=24, pady=(14, 4))
            SectionBar(shift_hdr, f"{shift} Shift",
                       color=SHIFT_CLR.get(shift, (ACCENT,))[0],
                       bg=BG_PAGE).pack(side="left")
            ShiftPill(shift_hdr, shift).pack(side="left", padx=8)

            n_foh = len(foh_by_shift[shift])
            tk.Label(scroll, text=f"{n_foh} FOH employee(s) in this shift",
                     bg=BG_PAGE, fg=FG_SEC, font=(FONT, 11)).pack(anchor="w", padx=28)

            inp_card = Card(scroll)
            inp_card.pack(fill="x", padx=24, pady=4)

            tk.Label(inp_card, text="Floor Tips $", bg=BG_CARD, fg=FG,
                     font=(FONT, 12)).grid(row=0, column=0, padx=8, pady=6, sticky="w")
            fe = Inp(inp_card, width=12)
            fe.grid(row=0, column=1, padx=8, pady=6)
            saved_fl = self._saved_tip_totals.get(shift, {}).get("floor", 0)
            fe.insert(0, str(round(saved_fl, 2)) if saved_fl else "0")

            tk.Label(inp_card, text="Bar Tips $", bg=BG_CARD, fg=FG,
                     font=(FONT, 12)).grid(row=1, column=0, padx=8, pady=6, sticky="w")
            be = Inp(inp_card, width=12)
            be.grid(row=1, column=1, padx=8, pady=6)
            saved_br = self._saved_tip_totals.get(shift, {}).get("bar", 0)
            be.insert(0, str(round(saved_br, 2)) if saved_br else "0")

            self._shift_tip_entries[shift] = {"floor": fe, "bar": be}

            Btn(inp_card, text="Calculate Distribution", style="primary",
                command=lambda s=shift: self._calc_tips(s)).grid(
                    row=2, column=0, columnspan=2, pady=10)

            disp = tk.Frame(scroll, bg=BG_PAGE)
            disp.pack(fill="x", padx=24)
            self._shift_tip_display[shift] = disp

            # Use snapshotted values (user-entered) if available, else saved values
            tip_vals = getattr(self, "_tip_entry_values", {}).get(shift, {})
            restore_fl = tip_vals.get("floor", saved_fl)
            restore_br = tip_vals.get("bar", saved_br)
            if tip_vals:
                # Overwrite the default saved values with what user had entered
                fe.delete(0, "end")
                fe.insert(0, str(round(restore_fl, 2)) if restore_fl else "0")
                be.delete(0, "end")
                be.insert(0, str(round(restore_br, 2)) if restore_br else "0")

            if restore_fl or restore_br:
                self.after(100, lambda s=shift: self._calc_tips(s))

    def _calc_tips(self, shift):
        disp = self._shift_tip_display.get(shift)
        if not disp:
            return
        for w in disp.winfo_children():
            w.destroy()

        entries = self._shift_tip_entries[shift]
        floor_t = safe_float(entries["floor"].get())
        bar_t = safe_float(entries["bar"].get())

        blocks = self._hours_data
        foh_blocks = [b for b in blocks
                      if b["shift"] == shift and
                      (self.dm.pos_by_name(b["position_name"]) or {}).get("department") == "FOH"]

        total_pts = 0
        floor_list = []
        for b in foh_blocks:
            pos = self.dm.pos_by_name(b["position_name"])
            pts = safe_float(pos.get("tip_points", 0)) if pos else 0
            total_pts += pts
            floor_list.append({
                "emp_id": b["emp_id"], "name": b["emp_name"],
                "position": b["position_name"], "points": pts, "amount": 0.0,
            })
        if total_pts > 0:
            vpp = floor_t / total_pts
            for e in floor_list:
                e["amount"] = round(e["points"] * vpp, 2)

        card = Card(disp)
        card.pack(fill="x", pady=4)
        tk.Label(card, text=f"Floor Tips: {fmt(floor_t)}    Total Points: {int(total_pts)}",
                 bg=BG_CARD, fg=ACCENT, font=(FONT, 12, "bold")).pack(anchor="w")
        if total_pts > 0:
            tk.Label(card, text=f"Value per point: {fmt(floor_t / total_pts)}",
                     bg=BG_CARD, fg=FG_SEC, font=(FONT, 11)).pack(anchor="w", pady=(0, 4))
        for i, e in enumerate(floor_list):
            bg = ROW_B if i % 2 else ROW_A
            r = tk.Frame(card, bg=bg)
            r.pack(fill="x")
            fl_name = tk.Label(r, text=e["name"], bg=bg, fg=ACCENT,
                               font=(FONT, 12, "bold"), width=22, anchor="w",
                               padx=8, cursor="hand2")
            fl_name.pack(side="left", pady=4)
            fl_emp = self.dm.emp_by_id(e["emp_id"])
            if fl_emp:
                fl_name.bind("<Button-1>", lambda ev, em=fl_emp: self._open_emp_profile(em))
            tk.Label(r, text=f'{e["position"]} ({int(e["points"])} pts)',
                     bg=bg, fg=FG_SEC, font=(FONT, 11), width=20, anchor="w").pack(side="left")
            tk.Label(r, text=fmt(e["amount"]), bg=bg, fg=SUCCESS,
                     font=(FONT, 12, "bold"), padx=10).pack(side="right")

        bartenders = []
        barbacks = []
        for b in foh_blocks:
            pos = self.dm.pos_by_name(b["position_name"])
            if not pos:
                continue
            if pos.get("receives_bar_tips"):
                bartenders.append(b)
            bsp = safe_float(pos.get("bar_tip_share_pct", 0))
            if bsp > 0:
                barbacks.append((b, bsp))

        bar_list = []
        remaining = bar_t
        for b, pct in barbacks:
            share = round(bar_t * pct / 100, 2)
            remaining -= share
            bar_list.append({
                "emp_id": b["emp_id"], "name": b["emp_name"],
                "amount": share, "role": f'{b["position_name"]} ({pct:.0f}%)',
            })
        if bartenders:
            each = round(remaining / len(bartenders), 2) if remaining > 0 else 0
            for b in bartenders:
                bar_list.append({
                    "emp_id": b["emp_id"], "name": b["emp_name"],
                    "amount": each, "role": b["position_name"],
                })

        card2 = Card(disp)
        card2.pack(fill="x", pady=4)
        tk.Label(card2, text=f"Bar Tips: {fmt(bar_t)}", bg=BG_CARD, fg="#E67E22",
                 font=(FONT, 12, "bold")).pack(anchor="w")
        if not bar_list:
            tk.Label(card2, text="No bartenders/barbacks for this shift.",
                     bg=BG_CARD, fg=FG_SEC, font=(FONT, 11)).pack(anchor="w", pady=4)
        for i, e in enumerate(bar_list):
            bg = ROW_B if i % 2 else ROW_A
            r = tk.Frame(card2, bg=bg)
            r.pack(fill="x")
            br_name = tk.Label(r, text=e["name"], bg=bg, fg=ACCENT,
                               font=(FONT, 12, "bold"), width=22, anchor="w",
                               padx=8, cursor="hand2")
            br_name.pack(side="left", pady=4)
            br_emp = self.dm.emp_by_id(e["emp_id"])
            if br_emp:
                br_name.bind("<Button-1>", lambda ev, em=br_emp: self._open_emp_profile(em))
            tk.Label(r, text=e["role"], bg=bg, fg=FG_SEC, font=(FONT, 11),
                     width=20, anchor="w").pack(side="left")
            tk.Label(r, text=fmt(e["amount"]), bg=bg, fg=SUCCESS,
                     font=(FONT, 12, "bold"), padx=10).pack(side="right")

        self._day_tips[shift] = {
            "floor_tips": floor_t, "bar_tips": bar_t,
            "floor_breakdown": floor_list, "bar_breakdown": bar_list,
        }
        self._update_footer()

    # ── Save Day ──────────────────────────────────────────────────────────
    def _save_day(self):
        self._snapshot_hours_from_widgets()
        self._snapshot_checked_from_widgets()
        self._snapshot_tips_from_widgets()

        if hasattr(self, "_shift_tip_entries"):
            for shift in self._shift_tip_entries:
                if shift not in self._day_tips:
                    try:
                        self._calc_tips(shift)
                    except Exception:
                        pass

        day_name = DAYS[self.sel_date.weekday()]
        blocks = [h for h in self._hours_data if h["emp_id"] in self._checked_emp_ids]
        tips = self._day_tips

        if not blocks:
            messagebox.showwarning("No Data", "No employees are checked. Nothing to save.")
            return

        has_zero = any(b["hours"] == 0 for b in blocks)

        foh_saved, boh_saved, _ = self.dm.load_day(self.cur_mon, day_name)
        if foh_saved or boh_saved:
            if not messagebox.askyesno("Confirm",
                    f"This will update the saved data for "
                    f"{self.sel_date.strftime('%A, %b %d')}. Continue?"):
                return

        self.dm.save_day(self.cur_mon, day_name, blocks, tips)

        msg = f"Day saved \u2014 {day_name}!"
        if has_zero:
            msg += "  (Some shifts have 0 hours)"
        self.toast.show(msg)

    # ══════════════════════════════════════════════════════════════════════
    #  WEEK VIEW — 7-day grid + labor cost in red + collapsible tables
    # ══════════════════════════════════════════════════════════════════════
    def pg_week(self):
        scroll = ScrollFrame(self.main, bg=BG_PAGE)
        scroll.pack(fill="both", expand=True)
        mon = self.cur_mon

        hdr = tk.Frame(scroll, bg=BG_PAGE)
        hdr.pack(fill="x", padx=24, pady=(18, 10))
        tk.Label(hdr,
                 text=f"Week View \u2014 {mon.strftime('%b %d')} to "
                      f"{(mon + timedelta(6)).strftime('%b %d, %Y')}",
                 bg=BG_PAGE, fg=FG, font=(FONT, 18, "bold")).pack(side="left")

        wnav = tk.Frame(scroll, bg=BG_PAGE)
        wnav.pack(fill="x", padx=24, pady=4)
        Btn(wnav, text="\u2190 Prev Week", style="ghost",
            command=lambda: self._chg_wk(-7)).pack(side="left", padx=4)
        Btn(wnav, text="Next Week \u2192", style="ghost",
            command=lambda: self._chg_wk(7)).pack(side="left", padx=4)

        grid_frame = tk.Frame(scroll, bg=BG_PAGE)
        grid_frame.pack(fill="x", padx=24, pady=(10, 4))

        for col in range(7):
            grid_frame.columnconfigure(col, weight=1)

        for i, day in enumerate(DAYS):
            dd = mon + timedelta(days=i)
            day_hdr = tk.Frame(grid_frame, bg=BG_NAV)
            day_hdr.grid(row=0, column=i, sticky="nswe", padx=1, pady=1)
            tk.Label(day_hdr, text=f"{day[:3]}\n{dd.strftime('%b %d')}", bg=BG_NAV,
                     fg="#FFFFFF", font=(FONT, 10, "bold"), padx=4, pady=4,
                     justify="center").pack(fill="x")

        weekly_labor = 0.0

        for i, day in enumerate(DAYS):
            dd = mon + timedelta(days=i)
            is_today = dd == date.today()
            border_color = ACCENT if is_today else BORDER

            cell_outer = tk.Frame(grid_frame, bg=border_color,
                                  highlightbackground=border_color,
                                  highlightthickness=2 if is_today else 1)
            cell_outer.grid(row=1, column=i, sticky="nswe", padx=1, pady=1)

            cell = tk.Frame(cell_outer, bg=BG_CARD, cursor="hand2")
            cell.pack(fill="both", expand=True, padx=1, pady=1)
            cell.bind("<Button-1>", lambda e, d=dd: self._edit_day(d))

            foh, boh, tips = self.dm.load_day(mon, day)
            allr = foh + boh
            th = sum(safe_float(r.get("hours", 0)) for r in allr)
            tt = sum(safe_float(r.get("total_tip", 0)) for r in tips)
            unique_emps = len(set(r.get("emp_id") for r in allr))

            # Compute daily labor cost
            day_labor = self.dm.day_labor_cost(mon, day)
            weekly_labor += day_labor

            if not allr:
                empty_lbl = tk.Label(cell, text="No shifts", bg=BG_CARD, fg=FG_SEC,
                                     font=(FONT, 10), cursor="hand2", pady=16)
                empty_lbl.pack(fill="x")
                empty_lbl.bind("<Button-1>", lambda e, d=dd: self._edit_day(d))
            else:
                # Check: only show ✓ if ALL employees have hours > 0
                all_hours_filled = all(
                    safe_float(r.get("hours", 0)) > 0 for r in allr)
                if dd < date.today() and all_hours_filled:
                    dot = tk.Label(cell, text="\u2713", bg=BG_CARD, fg=SUCCESS,
                                   font=(FONT, 10, "bold"), cursor="hand2")
                    dot.pack(anchor="ne", padx=4)
                    dot.bind("<Button-1>", lambda e, d=dd: self._edit_day(d))
                elif dd < date.today() and not all_hours_filled:
                    dot = tk.Label(cell, text="\u26A0", bg=BG_CARD, fg=WARN_BORD,
                                   font=(FONT, 10, "bold"), cursor="hand2")
                    dot.pack(anchor="ne", padx=4)
                    dot.bind("<Button-1>", lambda e, d=dd: self._edit_day(d))

                def _make_cell_lbl(parent, txt, fg_c=FG, fnt_size=9, bold=False, dd_ref=dd):
                    weight = "bold" if bold else "normal"
                    lb = tk.Label(parent, text=txt, bg=BG_CARD, fg=fg_c,
                                  font=(FONT, fnt_size, weight), cursor="hand2",
                                  anchor="w", padx=4)
                    lb.pack(fill="x")
                    lb.bind("<Button-1>", lambda e, d=dd_ref: self._edit_day(d))

                _make_cell_lbl(cell, f"{unique_emps} employees", FG, 9, dd_ref=dd)

                shift_counts = {}
                for r in allr:
                    s = r.get("shift", "Dinner")
                    shift_counts[s] = shift_counts.get(s, 0) + 1
                shift_parts = []
                for s in SHIFTS:
                    if s in shift_counts:
                        shift_parts.append(f"{s[0]}:{shift_counts[s]}")
                _make_cell_lbl(cell, " | ".join(shift_parts), FG_SEC, 8, dd_ref=dd)
                _make_cell_lbl(cell, fmt(tt), SUCCESS, 9, bold=True, dd_ref=dd)
                _make_cell_lbl(cell, f"{th:.1f} hrs", FG_SEC, 9, dd_ref=dd)

                # Labor cost in RED
                if day_labor > 0:
                    _make_cell_lbl(cell, f"\U0001F4B8 {fmt(day_labor)}", DANGER, 9, bold=True, dd_ref=dd)

        # Weekly labor total row
        total_row = tk.Frame(scroll, bg=BG_PAGE)
        total_row.pack(fill="x", padx=24, pady=(4, 12))
        tk.Label(total_row, text=f"Weekly Labor: {fmt(weekly_labor)}", bg=BG_PAGE,
                 fg=DANGER, font=(FONT, 14, "bold")).pack(side="right", padx=8)

        # Collapsible detail tables
        folder = self.dm.wk(mon)

        for title, csv_file, fields in [
            ("FOH Hours", "foh_hours.csv", ["Employee", "Position", "Shift", "Date", "Hours"]),
            ("BOH Hours", "boh_hours.csv", ["Employee", "Position", "Shift", "Date", "Hours"]),
            ("Tips", "weekly_tips.csv", ["Date", "Shift", "Employee", "Floor Tips", "Bar Tips", "Total"]),
        ]:
            section_frame = tk.Frame(scroll, bg=BG_PAGE)
            section_frame.pack(fill="x", padx=24, pady=(8, 0))

            hdr_bar = tk.Frame(section_frame, bg=BG_CARD, highlightbackground=BORDER,
                               highlightthickness=1)
            hdr_bar.pack(fill="x")

            collapsed_var = tk.BooleanVar(value=False)
            content_frame = tk.Frame(section_frame, bg=BG_PAGE)

            def make_toggle(cf, cv, arrow_lbl):
                def toggle():
                    if cv.get():
                        cf.pack_forget()
                        cv.set(False)
                        arrow_lbl.config(text="\u25B6")
                    else:
                        cf.pack(fill="x")
                        cv.set(True)
                        arrow_lbl.config(text="\u25BC")
                return toggle

            arrow = tk.Label(hdr_bar, text="\u25B6", bg=BG_CARD, fg=ACCENT,
                             font=(FONT, 12), cursor="hand2", padx=8)
            arrow.pack(side="left")

            toggle_fn = make_toggle(content_frame, collapsed_var, arrow)
            arrow.bind("<Button-1>", lambda e, fn=toggle_fn: fn())

            title_lbl = tk.Label(hdr_bar, text=title, bg=BG_CARD, fg=FG,
                                 font=(FONT, 13, "bold"), cursor="hand2", padx=4, pady=8)
            title_lbl.pack(side="left")
            title_lbl.bind("<Button-1>", lambda e, fn=toggle_fn: fn())

            csv_path = folder / csv_file
            Btn(hdr_bar, text="Export CSV", style="export",
                command=lambda p=csv_path, t=title: self._export_wk_csv(p, t)).pack(
                side="right", padx=8, pady=4)

            rows = self.dm.read_csv(csv_path)
            if not rows:
                tk.Label(content_frame, text="No data this week yet",
                         bg=BG_PAGE, fg=FG_SEC, font=(FONT, 12)).pack(
                    anchor="w", padx=8, pady=10)
            else:
                tbl_card = Card(content_frame)
                tbl_card.pack(fill="x", pady=4)

                is_hours = "foh_hours" in csv_file or "boh_hours" in csv_file
                if is_hours:
                    csv_keys = ["employee_name", "position", "shift", "day", "hours"]
                else:
                    csv_keys = ["day", "shift", "employee_name", "floor_tip", "bar_tip", "total_tip"]

                for j, f_name in enumerate(fields):
                    tk.Label(tbl_card, text=f_name, bg=BG_CARD, fg=FG_HDR,
                             font=(FONT, 10, "bold"), width=14, anchor="w",
                             padx=6, pady=6).grid(row=0, column=j, sticky="we")
                tk.Frame(tbl_card, bg=BORDER, height=1).grid(
                    row=1, column=0, columnspan=len(fields) + 1, sticky="we")

                for ri, row in enumerate(rows):
                    bg = ROW_B if ri % 2 else ROW_A
                    for j, key in enumerate(csv_keys):
                        val = row.get(key, "")
                        if key in ("floor_tip", "bar_tip", "total_tip"):
                            val = fmt(val)
                        if key == "employee_name":
                            eid = row.get("emp_id", "")
                            emp_obj = self.dm.emp_by_id(eid) if eid else None
                            nl = tk.Label(tbl_card, text=str(val), bg=bg,
                                          fg=ACCENT, font=(FONT, 10, "bold"),
                                          width=14, anchor="w", padx=6, pady=4,
                                          cursor="hand2")
                            nl.grid(row=ri + 2, column=j, sticky="we")
                            if emp_obj:
                                nl.bind("<Button-1>",
                                        lambda e, em=emp_obj: self._open_emp_profile(em))
                        else:
                            tk.Label(tbl_card, text=str(val), bg=bg, fg=FG,
                                     font=(FONT, 10), width=14, anchor="w",
                                     padx=6, pady=4).grid(row=ri + 2, column=j, sticky="we")
                    edit_btn = tk.Label(tbl_card, text="\u270F Edit", bg=bg, fg=ACCENT,
                                        font=(FONT, 10, "bold"), cursor="hand2", padx=4)
                    edit_btn.grid(row=ri + 2, column=len(fields), sticky="we")
                    edit_btn.bind("<Button-1>",
                                 lambda e, r=row, cp=csv_path, ck=csv_keys, ih=is_hours:
                                     self._edit_wv_row(r, cp, ck, ih))

    def _edit_wv_row(self, row_data, csv_path, csv_keys, is_hours):
        """Open inline edit dialog for a single row in week view tables."""
        win = tk.Toplevel(self)
        win.title("Edit Row")
        win.configure(bg=BG_CARD)
        win.geometry("500x420")
        win.transient(self)
        win.grab_set()

        tk.Label(win, text="Edit Entry (Direct Override)",
                 bg=BG_CARD, fg=ACCENT, font=(FONT, 15, "bold")).pack(pady=(16, 12))

        entries = {}
        if is_hours:
            edit_fields = [
                ("employee_name", "Employee", True),
                ("position", "Position", False),
                ("shift", "Shift", False),
                ("day", "Day", True),
                ("hours", "Hours", False),
            ]
        else:
            edit_fields = [
                ("day", "Day", True),
                ("shift", "Shift", True),
                ("employee_name", "Employee", True),
                ("floor_tip", "Floor Tips ($)", False),
                ("bar_tip", "Bar Tips ($)", False),
                ("total_tip", "Total Tip ($)", False),
            ]

        form = tk.Frame(win, bg=BG_CARD)
        form.pack(fill="x", padx=28)

        for key, label, readonly in edit_fields:
            tk.Label(form, text=label, bg=BG_CARD, fg=FG_SEC,
                     font=(FONT, 11), anchor="w").pack(fill="x", pady=(6, 0))
            if key == "shift" and is_hours:
                var = tk.StringVar(value=row_data.get(key, "Dinner"))
                cb = ttk.Combobox(form, textvariable=var, values=SHIFTS,
                                  state="readonly", font=(FONT, 12), width=26)
                cb.pack(fill="x", pady=(0, 4))
                entries[key] = var
            elif key == "position" and is_hours:
                pos_names = [p["name"] for p in self.dm.positions]
                var = tk.StringVar(value=row_data.get(key, ""))
                cb = ttk.Combobox(form, textvariable=var, values=pos_names,
                                  state="readonly", font=(FONT, 12), width=26)
                cb.pack(fill="x", pady=(0, 4))
                entries[key] = var
            elif readonly:
                lbl = tk.Label(form, text=str(row_data.get(key, "")),
                               bg=BG_PAGE, fg=FG, font=(FONT, 12),
                               anchor="w", padx=6, pady=4)
                lbl.pack(fill="x", pady=(0, 4))
                entries[key] = None  # read-only, keep original value
            else:
                e = Inp(form, width=28)
                e.pack(fill="x", pady=(0, 4))
                e.insert(0, str(row_data.get(key, "")))
                entries[key] = e

        btn_frame = tk.Frame(win, bg=BG_CARD)
        btn_frame.pack(pady=16)

        def save_edit():
            # Read all rows from csv, find matching row, update it
            all_rows = self.dm.read_csv(csv_path)
            # Find the matching row by comparing all original values
            matched = False
            for r in all_rows:
                match = all(str(r.get(k, "")) == str(row_data.get(k, ""))
                            for k in row_data.keys())
                if match and not matched:
                    matched = True
                    for key, widget in entries.items():
                        if widget is None:
                            continue  # read-only field
                        if isinstance(widget, tk.StringVar):
                            r[key] = widget.get()
                        else:
                            r[key] = widget.get()
                    # For tips, recalculate total_tip if floor/bar changed
                    if not is_hours:
                        ft = safe_float(r.get("floor_tip", 0))
                        bt = safe_float(r.get("bar_tip", 0))
                        r["total_tip"] = str(round(ft + bt, 2))
                    break

            if matched:
                # Write back the entire csv
                if all_rows:
                    fieldnames = list(all_rows[0].keys())
                    self.dm.write_csv(csv_path, fieldnames, all_rows)
                win.destroy()
                self._clr()
                self.pg_week()
                self.toast.show("Row updated!")
            else:
                messagebox.showwarning("Error", "Could not find matching row.", parent=win)

        def delete_row():
            if not messagebox.askyesno("Confirm", "Delete this row?", parent=win):
                return
            all_rows = self.dm.read_csv(csv_path)
            new_rows = []
            removed = False
            for r in all_rows:
                match = all(str(r.get(k, "")) == str(row_data.get(k, ""))
                            for k in row_data.keys())
                if match and not removed:
                    removed = True
                    continue
                new_rows.append(r)
            if new_rows:
                fieldnames = list(new_rows[0].keys())
                self.dm.write_csv(csv_path, fieldnames, new_rows)
            elif csv_path.exists():
                csv_path.unlink()
            win.destroy()
            self._clr()
            self.pg_week()
            self.toast.show("Row deleted.")

        Btn(btn_frame, text="\u2713  Save", command=save_edit, style="primary").pack(side="left", padx=8)
        Btn(btn_frame, text="\U0001F5D1 Delete Row", command=delete_row, style="danger").pack(side="left", padx=8)
        Btn(btn_frame, text="Cancel", command=win.destroy, style="cancel").pack(side="left", padx=8)

    def _export_wk_csv(self, path, title):
        if not path.exists():
            self.toast.show("No data to export.", bg=WARN_BG, fg=WARN_FG)
            return
        dest = filedialog.asksaveasfilename(
            title=f"Export {title}",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=path.name,
        )
        if not dest:
            return
        import shutil
        shutil.copy2(str(path), dest)
        self.toast.show(f"Exported \u2192 {Path(dest).name}")

    def _chg_wk(self, d):
        self.sel_date += timedelta(days=d)
        self.cur_mon = monday_of(self.sel_date)
        self._upd_date()
        self._clr()
        self.pg_week()

    def _edit_day(self, d):
        self.sel_date = d
        self.cur_mon = monday_of(d)
        self._upd_date()
        self.nav_click("Today")

    # ══════════════════════════════════════════════════════════════════════
    #  PAYROLL REPORT — Total Labor (renamed from Grand Total), wage notes
    # ══════════════════════════════════════════════════════════════════════
    def pg_payroll(self):
        scroll = ScrollFrame(self.main, bg=BG_PAGE)
        scroll.pack(fill="both", expand=True)
        mon = self.cur_mon

        tk.Label(scroll, text=f"Payroll Report \u2014 Week of {mon.strftime('%b %d, %Y')}",
                 bg=BG_PAGE, fg=FG, font=(FONT, 18, "bold")).pack(
                     anchor="w", padx=24, pady=(18, 10))

        payroll = self.dm.gen_payroll(mon)
        if not payroll:
            card = Card(scroll)
            card.pack(fill="x", padx=24, pady=20)
            tk.Label(card, text="No shifts logged this week yet",
                     bg=BG_CARD, fg=FG_SEC, font=(FONT, 13)).pack(pady=16)
            return

        foh_t = sum(r["total_compensation"] for r in payroll if r["department"] == "FOH")
        boh_t = sum(r["total_compensation"] for r in payroll if r["department"] == "BOH")
        tip_t = sum(r["total_tips"] for r in payroll)
        wages_only = sum(r["regular_wages"] + r["overtime_wages"] for r in payroll)
        grand = sum(r["total_compensation"] for r in payroll)

        cards_row = tk.Frame(scroll, bg=BG_PAGE)
        cards_row.pack(fill="x", padx=24, pady=10)
        for label, val, color in [("FOH Payroll", foh_t, ACCENT),
                                   ("BOH Payroll", boh_t, "#E67E22"),
                                   ("Total Tips", tip_t, SUCCESS),
                                   ("Total Wages", wages_only, FG_HDR),
                                   ("Total Labor", grand, DANGER)]:
            c = Card(cards_row)
            c.pack(side="left", fill="x", expand=True, padx=4)
            tk.Label(c, text=label, bg=BG_CARD, fg=FG_SEC,
                     font=(FONT, 11)).pack(anchor="w")
            tk.Label(c, text=fmt(val), bg=BG_CARD, fg=color,
                     font=(FONT, 22, "bold")).pack(anchor="w")

        card = Card(scroll)
        card.pack(fill="x", padx=24, pady=10)
        cols = ["Employee", "Position(s)", "Dept", "Reg Hrs", "OT Hrs",
                "Rate", "Reg Wages", "OT Wages", "Tips", "Total"]
        col_widths = [20, 16, 7, 8, 8, 8, 11, 11, 11, 12]
        for j, c in enumerate(cols):
            tk.Label(card, text=c, bg=BG_CARD, fg=FG_HDR,
                     font=(FONT, 11, "bold"), width=col_widths[j], anchor="w",
                     padx=6, pady=8).grid(row=0, column=j, sticky="we")
        tk.Frame(card, bg=BORDER, height=1).grid(
            row=1, column=0, columnspan=len(cols), sticky="we")

        grid_row = 2  # track actual grid row (wage notes take extra rows)
        for i, r in enumerate(payroll):
            bg = ROW_B if i % 2 else ROW_A
            rate_str = "split" if r["hourly_rate"] == "split" else fmt(r["hourly_rate"])
            vals = [
                r["employee_name"], r["positions"], r["department"],
                f'{r["regular_hours"]:.1f}', f'{r["overtime_hours"]:.1f}',
                rate_str, fmt(r["regular_wages"]),
                fmt(r["overtime_wages"]), fmt(r["total_tips"]),
                fmt(r["total_compensation"]),
            ]
            for j, v in enumerate(vals):
                fg_c = SUCCESS if j == 9 else FG
                if j == 0:
                    # Employee name — clickable to open profile
                    emp_obj = self.dm.emp_by_id(r["emp_id"])
                    name_lbl = tk.Label(card, text=v, bg=bg, fg=ACCENT,
                                        font=(FONT, 11, "bold"),
                                        width=col_widths[j], anchor="w",
                                        padx=6, pady=4, cursor="hand2")
                    name_lbl.grid(row=grid_row, column=j, sticky="we")
                    if emp_obj:
                        name_lbl.bind("<Button-1>",
                                      lambda e, em=emp_obj: self._open_emp_profile(em))
                elif j == 2:
                    cell_f = tk.Frame(card, bg=bg)
                    cell_f.grid(row=grid_row, column=j, sticky="we")
                    DeptPill(cell_f, v).pack(side="left", padx=6, pady=4)
                else:
                    tk.Label(card, text=v, bg=bg, fg=fg_c, font=(FONT, 11),
                             width=col_widths[j], anchor="w", padx=6,
                             pady=4).grid(row=grid_row, column=j, sticky="we")
            grid_row += 1

            # Wage note for split-wage employees — on its OWN row below
            if r.get("wage_note"):
                tk.Label(card, text=f"  \u2514 {r['wage_note']}", bg=bg, fg=FG_SEC,
                         font=(FONT, 9), anchor="w", padx=6).grid(
                    row=grid_row, column=0, columnspan=len(cols), sticky="w", pady=(0, 2))
                grid_row += 1

        # Total Labor summary row
        tk.Frame(card, bg=ACCENT, height=2).grid(
            row=grid_row, column=0, columnspan=len(cols), sticky="we")
        grid_row += 1

        total_wages = sum(r["regular_wages"] + r["overtime_wages"] for r in payroll)
        total_ot = sum(r["overtime_wages"] for r in payroll)
        total_tips = sum(r["total_tips"] for r in payroll)
        total_all = sum(r["total_compensation"] for r in payroll)

        for j, v in enumerate(["Total Labor", "", "", "", "", "",
                                fmt(total_wages), fmt(total_ot),
                                fmt(total_tips), fmt(total_all)]):
            fg_c = DANGER  # all red in Total Labor row
            tk.Label(card, text=v, bg=TOTAL_LABOR_BG, fg=fg_c,
                     font=(FONT, 13 if j == 0 or j == 9 else 11, "bold"),
                     width=col_widths[j], anchor="w", padx=6,
                     pady=6).grid(row=grid_row, column=j, sticky="we")

        btn_row = tk.Frame(scroll, bg=BG_PAGE)
        btn_row.pack(fill="x", padx=24, pady=14)
        Btn(btn_row, text="Export Payroll to CSV", style="export",
            command=lambda: self._do_export(mon, payroll)).pack(side="right")

    def _do_export(self, mon, rows):
        p = self.dm.export_payroll(mon, rows)
        dest = filedialog.asksaveasfilename(
            title="Export Payroll CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=p.name,
        )
        if not dest:
            return
        import shutil
        shutil.copy2(str(p), dest)
        self.toast.show(f"Payroll exported \u2192 {Path(dest).name}")

    # ══════════════════════════════════════════════════════════════════════
    #  EMPLOYEE WEEKLY ACTIVITY PROFILE
    # ══════════════════════════════════════════════════════════════════════
    def _open_emp_profile(self, emp, profile_mon=None):
        """Open a large modal showing an employee's full weekly activity."""
        if not emp:
            return
        if profile_mon is None:
            profile_mon = self.cur_mon

        win = tk.Toplevel(self)
        win.title(f"Employee Profile — {emp['name']}")
        win.configure(bg=BG_PAGE)
        win.geometry("900x680")
        win.minsize(700, 550)
        win.transient(self)
        win.grab_set()

        # State for week navigation inside the profile
        profile_state = {"mon": profile_mon}

        # Close button
        close_btn = tk.Label(win, text="\u2715", bg=BG_PAGE, fg=FG_SEC,
                             font=(FONT, 18), cursor="hand2", padx=8)
        close_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-8, y=8)
        close_btn.bind("<Button-1>", lambda e: win.destroy())

        # Container that gets rebuilt on week nav
        container = tk.Frame(win, bg=BG_PAGE)
        container.pack(fill="both", expand=True)

        def build_profile():
            for w in container.winfo_children():
                w.destroy()

            mon = profile_state["mon"]

            scroll = ScrollFrame(container, bg=BG_PAGE)
            scroll.pack(fill="both", expand=True)

            # ── Header ────────────────────────────────────────────────────
            hdr = tk.Frame(scroll, bg=BG_CARD, highlightbackground=BORDER,
                           highlightthickness=1)
            hdr.pack(fill="x", padx=20, pady=(16, 8))

            hdr_left = tk.Frame(hdr, bg=BG_CARD)
            hdr_left.pack(side="left", fill="x", expand=True, padx=16, pady=12)

            name_row = tk.Frame(hdr_left, bg=BG_CARD)
            name_row.pack(fill="x")
            tk.Label(name_row, text=emp["name"], bg=BG_CARD, fg=FG,
                     font=(FONT, 20, "bold")).pack(side="left")
            dept = self.dm.emp_dept(emp)
            DeptPill(name_row, dept).pack(side="left", padx=10)

            tk.Label(hdr_left, text=f"ID: {emp['id']}", bg=BG_CARD, fg=FG_SEC,
                     font=("Consolas", 10)).pack(anchor="w", pady=(2, 6))

            pos_row = tk.Frame(hdr_left, bg=BG_CARD)
            pos_row.pack(fill="x")
            for a in emp.get("positions", []):
                pn = a["position_name"]
                wage = self.dm.get_wage(pn)
                pill = tk.Label(pos_row, text=f" {pn} ({fmt(wage)}/hr) ",
                                bg="#EEF2FF", fg=ACCENT, font=(FONT, 10, "bold"),
                                padx=6, pady=2)
                pill.pack(side="left", padx=(0, 6))

            Btn(hdr, text="\u270F\uFE0F  Edit Employee", style="primary",
                command=lambda: [win.destroy(), self._emp_dlg(emp)]).pack(
                side="right", padx=16, pady=12)

            # ── Week Navigation ───────────────────────────────────────────
            wk_nav = tk.Frame(scroll, bg=BG_PAGE)
            wk_nav.pack(fill="x", padx=20, pady=(8, 4))

            def prev_wk():
                profile_state["mon"] = mon - timedelta(days=7)
                build_profile()

            def next_wk():
                profile_state["mon"] = mon + timedelta(days=7)
                build_profile()

            Btn(wk_nav, text="\u2190  Previous Week", style="cancel",
                command=prev_wk).pack(side="left", padx=4)
            tk.Label(wk_nav,
                     text=f"Week of {mon.strftime('%a %b %d')} \u2014 "
                          f"{(mon + timedelta(6)).strftime('%a %b %d, %Y')}",
                     bg=BG_PAGE, fg=FG, font=(FONT, 13, "bold")).pack(side="left", padx=12)
            Btn(wk_nav, text="Next Week  \u2192", style="cancel",
                command=next_wk).pack(side="left", padx=4)

            # ── Fetch Data ────────────────────────────────────────────────
            data = self.dm.emp_weekly_profile(mon, emp["id"])

            # ── Empty State ───────────────────────────────────────────────
            if data["days_worked"] == 0 and data["total_tips"] == 0:
                empty = Card(scroll)
                empty.pack(fill="x", padx=20, pady=30)
                tk.Label(empty, text="\U0001F4AD", bg=BG_CARD, fg=FG_SEC,
                         font=(FONT, 36)).pack(pady=(16, 6))
                tk.Label(empty, text=f"{emp['name']} has no logged shifts this week",
                         bg=BG_CARD, fg=FG_SEC, font=(FONT, 14)).pack(pady=(0, 20))
                return

            # ── Summary Cards ─────────────────────────────────────────────
            cards_row = tk.Frame(scroll, bg=BG_PAGE)
            cards_row.pack(fill="x", padx=20, pady=(8, 10))

            stat_items = [
                ("\U0001F4C5", "Days Worked", str(data["days_worked"]), ACCENT),
                ("\u23F1", "Total Hours", f'{data["total_hours"]:.1f}', "#0891B2"),
                ("\U0001F4B0", "Total Tips", fmt(data["total_tips"]), SUCCESS),
                ("\U0001F4B5", "Total Wages", fmt(data["total_wages"]), "#E67E22"),
            ]
            for icon, label, value, color in stat_items:
                c = Card(cards_row)
                c.pack(side="left", fill="x", expand=True, padx=4)
                tk.Label(c, text=icon, bg=BG_CARD, fg=color,
                         font=(FONT, 22)).pack(anchor="w")
                tk.Label(c, text=value, bg=BG_CARD, fg=color,
                         font=(FONT, 22, "bold")).pack(anchor="w")
                tk.Label(c, text=label, bg=BG_CARD, fg=FG_SEC,
                         font=(FONT, 10)).pack(anchor="w")

            # ── Daily Breakdown Table (editable hours) ─────────────────────
            edit_hdr = tk.Frame(scroll, bg=BG_PAGE)
            edit_hdr.pack(fill="x", padx=20, pady=(10, 4))
            SectionBar(edit_hdr, "Daily Breakdown", color=ACCENT, bg=BG_PAGE).pack(
                side="left")
            # Track editable hours entries: list of {day, shift, position, entry_widget}
            profile_hours_entries = []

            def save_profile_hours():
                """Save edited hours from profile back to the day data."""
                # Group changes by day
                changes_by_day = {}
                for phe in profile_hours_entries:
                    day_n = phe["day"]
                    new_hrs = safe_float(phe["widget"].get())
                    changes_by_day.setdefault(day_n, []).append({
                        "day": day_n, "shift": phe["shift"],
                        "position": phe["position"], "hours": new_hrs,
                        "emp_id": emp["id"], "emp_name": emp["name"],
                    })

                for day_n, new_blocks in changes_by_day.items():
                    # Load existing day data
                    foh_saved, boh_saved, tip_saved = self.dm.load_day(mon, day_n)
                    all_rows = foh_saved + boh_saved

                    # Update this employee's hours in the existing rows
                    for nb in new_blocks:
                        matched = False
                        for r in all_rows:
                            if (r.get("emp_id") == emp["id"] and
                                r.get("shift") == nb["shift"] and
                                r.get("position") == nb["position"]):
                                r["hours"] = nb["hours"]
                                matched = True
                                break
                        if not matched:
                            # New entry — add it
                            all_rows.append({
                                "emp_id": emp["id"],
                                "employee_name": emp["name"],
                                "position": nb["position"],
                                "shift": nb["shift"],
                                "hours": nb["hours"],
                                "day": day_n,
                            })

                    # Rebuild blocks in the format save_day expects
                    save_blocks = []
                    for r in all_rows:
                        save_blocks.append({
                            "emp_id": r.get("emp_id", ""),
                            "emp_name": r.get("employee_name", ""),
                            "position_name": r.get("position", ""),
                            "shift": r.get("shift", "Dinner"),
                            "hours": safe_float(r.get("hours", 0)),
                        })

                    # Rebuild tips dict from tip_saved
                    tips_dict = {}
                    for t in tip_saved:
                        shift = t.get("shift", "Dinner")
                        if shift not in tips_dict:
                            tips_dict[shift] = {
                                "floor_tips": 0, "bar_tips": 0,
                                "floor_breakdown": [], "bar_breakdown": [],
                            }
                        ft = safe_float(t.get("floor_tip", 0))
                        bt = safe_float(t.get("bar_tip", 0))
                        tips_dict[shift]["floor_tips"] += ft
                        tips_dict[shift]["bar_tips"] += bt
                        if ft > 0:
                            tips_dict[shift]["floor_breakdown"].append({
                                "emp_id": t.get("emp_id", ""),
                                "name": t.get("employee_name", ""),
                                "position": t.get("position", ""),
                                "points": safe_float(t.get("points", 0)),
                                "amount": ft,
                            })
                        if bt > 0:
                            tips_dict[shift]["bar_breakdown"].append({
                                "emp_id": t.get("emp_id", ""),
                                "name": t.get("employee_name", ""),
                                "role": t.get("position", ""),
                                "amount": bt,
                            })

                    self.dm.save_day(mon, day_n, save_blocks, tips_dict)

                # Refresh profile
                build_profile()
                self.toast.show("Hours updated!")

            save_btn = Btn(edit_hdr, text="\u2713  Save Hours", style="primary",
                           command=save_profile_hours)
            save_btn.pack(side="right", padx=4)

            tbl = Card(scroll)
            tbl.pack(fill="x", padx=20, pady=4)

            tbl_cols = ["Date", "Day", "Shift", "Position", "Hours",
                        "Wage/hr", "Wages", "Floor Tips", "Bar Tips",
                        "Total Tips", "Day Total"]
            tbl_widths = [10, 8, 8, 12, 6, 7, 9, 9, 9, 9, 10]

            for j, c in enumerate(tbl_cols):
                tk.Label(tbl, text=c, bg=BG_CARD, fg=FG_HDR,
                         font=(FONT, 9, "bold"), width=tbl_widths[j],
                         anchor="w", padx=4, pady=6).grid(row=0, column=j, sticky="we")
            tk.Frame(tbl, bg=BORDER, height=1).grid(
                row=1, column=0, columnspan=len(tbl_cols), sticky="we")

            grid_row = 2
            running_total_hours = 0.0
            running_total_wages = 0.0
            running_total_ot_wages = 0.0
            running_total_floor = 0.0
            running_total_bar = 0.0
            running_total_comp = 0.0

            # Sort days in DAYS order
            sorted_days = [d for d in DAYS if d in data["day_data"]]

            for day_name in sorted_days:
                entries = data["day_data"][day_name]
                day_idx = DAYS.index(day_name)
                dd = mon + timedelta(days=day_idx)
                date_str = dd.strftime("%b %d")

                day_total_hrs = sum(e["hours"] for e in entries)
                day_total_earn = sum(e["wages"] + e["floor_tip"] + e["bar_tip"]
                                     for e in entries)

                # Day group header
                for j in range(len(tbl_cols)):
                    if j == 0:
                        txt = f"\U0001F4C5 {date_str}"
                    elif j == 1:
                        txt = day_name[:3]
                    elif j == 4:
                        txt = f"{day_total_hrs:.1f}h"
                    elif j == 10:
                        txt = fmt(day_total_earn)
                    else:
                        txt = ""
                    tk.Label(tbl, text=txt, bg="#EEF2FF", fg=ACCENT,
                             font=(FONT, 9, "bold"), width=tbl_widths[j],
                             anchor="w", padx=4, pady=4).grid(
                        row=grid_row, column=j, sticky="we")
                grid_row += 1

                for ei, entry in enumerate(entries):
                    bg = ROW_B if ei % 2 else ROW_A
                    hrs = entry["hours"]
                    hrs_str = f"{hrs:.1f}"
                    fl = entry["floor_tip"]
                    bt = entry["bar_tip"]
                    tt = fl + bt
                    day_entry_total = entry["wages"] + tt

                    running_total_hours += hrs
                    running_total_wages += entry["wages"]
                    running_total_floor += fl
                    running_total_bar += bt
                    running_total_comp += day_entry_total

                    vals = [
                        "", "", entry["shift"], entry["position"],
                        hrs_str, fmt(entry["hourly_wage"]),
                        fmt(entry["wages"]), fmt(fl), fmt(bt), fmt(tt),
                        fmt(day_entry_total),
                    ]
                    for j, v in enumerate(vals):
                        fg_c = FG
                        if j == 9:
                            fg_c = SUCCESS
                        elif j == 10:
                            fg_c = ACCENT
                        if j == 3:
                            # Position with dept pill
                            cell_f = tk.Frame(tbl, bg=bg)
                            cell_f.grid(row=grid_row, column=j, sticky="we")
                            pos_obj = self.dm.pos_by_name(entry["position"])
                            pos_dept = pos_obj.get("department", "FOH") if pos_obj else "FOH"
                            DeptPill(cell_f, pos_dept).pack(side="left", padx=2)
                            tk.Label(cell_f, text=entry["position"], bg=bg, fg=FG,
                                     font=(FONT, 9), anchor="w",
                                     padx=2).pack(side="left")
                        elif j == 4:
                            # Editable hours cell
                            hrs_entry = Inp(tbl, width=tbl_widths[j])
                            hrs_entry.insert(0, hrs_str)
                            hrs_entry.grid(row=grid_row, column=j, sticky="we",
                                           padx=2, pady=1)
                            profile_hours_entries.append({
                                "day": day_name, "shift": entry["shift"],
                                "position": entry["position"],
                                "widget": hrs_entry,
                            })
                        else:
                            tk.Label(tbl, text=v, bg=bg, fg=fg_c,
                                     font=(FONT, 9), width=tbl_widths[j],
                                     anchor="w", padx=4,
                                     pady=3).grid(row=grid_row, column=j, sticky="we")
                    grid_row += 1

            # ── Totals Row ────────────────────────────────────────────────
            tk.Frame(tbl, bg=ACCENT, height=2).grid(
                row=grid_row, column=0, columnspan=len(tbl_cols), sticky="we")
            grid_row += 1

            totals_vals = [
                "TOTAL", "", "", "",
                f"{running_total_hours:.1f}",
                "",
                fmt(running_total_wages), fmt(running_total_floor),
                fmt(running_total_bar),
                fmt(running_total_floor + running_total_bar),
                fmt(running_total_comp),
            ]
            for j, v in enumerate(totals_vals):
                fg_c = ACCENT if j == 10 else FG
                tk.Label(tbl, text=v, bg=TOTAL_LABOR_BG, fg=fg_c,
                         font=(FONT, 10, "bold"), width=tbl_widths[j],
                         anchor="w", padx=4,
                         pady=6).grid(row=grid_row, column=j, sticky="we")

        build_profile()


# ═══════════════════════════════════════════════════════════════════════════════
#  SEED DATA
# ═══════════════════════════════════════════════════════════════════════════════
def seed():
    if POS_FILE.exists() and EMP_FILE.exists():
        return

    positions = [
        {"name": "Bartender", "department": "FOH", "hourly_wage": 11.00,
         "fixed_weekly_wage": None, "overtime_rate": 1.5, "tip_points": 5,
         "bar_tip_share_pct": 0, "receives_bar_tips": True},
        {"name": "Server", "department": "FOH", "hourly_wage": 11.35,
         "fixed_weekly_wage": None, "overtime_rate": 1.5, "tip_points": 10,
         "bar_tip_share_pct": 0, "receives_bar_tips": False},
        {"name": "Runner", "department": "FOH", "hourly_wage": 16.50,
         "fixed_weekly_wage": None, "overtime_rate": 1.5, "tip_points": 7,
         "bar_tip_share_pct": 0, "receives_bar_tips": False},
        {"name": "Busser", "department": "FOH", "hourly_wage": 16.50,
         "fixed_weekly_wage": None, "overtime_rate": 1.5, "tip_points": 5,
         "bar_tip_share_pct": 0, "receives_bar_tips": False},
        {"name": "Barback", "department": "FOH", "hourly_wage": 16.50,
         "fixed_weekly_wage": None, "overtime_rate": 1.5, "tip_points": 2,
         "bar_tip_share_pct": 20, "receives_bar_tips": False},
        {"name": "Host", "department": "FOH", "hourly_wage": 16.50,
         "fixed_weekly_wage": None, "overtime_rate": 1.5, "tip_points": 0,
         "bar_tip_share_pct": 0, "receives_bar_tips": False},
        {"name": "Kitchen", "department": "BOH", "hourly_wage": 18.00,
         "fixed_weekly_wage": None, "overtime_rate": 1.5, "tip_points": 0,
         "bar_tip_share_pct": 0, "receives_bar_tips": False},
        {"name": "Dishwasher", "department": "BOH", "hourly_wage": 16.50,
         "fixed_weekly_wage": None, "overtime_rate": 1.5, "tip_points": 0,
         "bar_tip_share_pct": 0, "receives_bar_tips": False},
        {"name": "Cleaner", "department": "BOH", "hourly_wage": 16.50,
         "fixed_weekly_wage": None, "overtime_rate": 1.5, "tip_points": 0,
         "bar_tip_share_pct": 0, "receives_bar_tips": False},
        {"name": "Chef", "department": "BOH", "hourly_wage": 25.00,
         "fixed_weekly_wage": None, "overtime_rate": 1.5, "tip_points": 0,
         "bar_tip_share_pct": 0, "receives_bar_tips": False},
    ]

    employees = [
        {"id": gen_id(), "name": "Haris Nioulikos", "positions": [{"position_name": "Bartender"}], "sort_order": 0},
        {"id": gen_id(), "name": "Julia Yan", "positions": [{"position_name": "Bartender"}], "sort_order": 1},
        {"id": gen_id(), "name": "Kostas Stamkopoulos", "positions": [{"position_name": "Bartender"}], "sort_order": 2},
        {"id": gen_id(), "name": "Katerina Kapandriti", "positions": [{"position_name": "Server"}], "sort_order": 3},
        {"id": gen_id(), "name": "Theofilos Adalis", "positions": [{"position_name": "Server"}], "sort_order": 4},
        {"id": gen_id(), "name": "Froso Pavlidou", "positions": [{"position_name": "Server"}], "sort_order": 5},
        {"id": gen_id(), "name": "Sakis Natsis", "positions": [{"position_name": "Server"}], "sort_order": 6},
        {"id": gen_id(), "name": "Mariana Kapandriti", "positions": [{"position_name": "Server"}], "sort_order": 7},
        {"id": gen_id(), "name": "Daniel Vilchis", "positions": [{"position_name": "Runner"}], "sort_order": 8},
        {"id": gen_id(), "name": "Juan El Boliviano", "positions": [{"position_name": "Runner"}, {"position_name": "Busser"}], "sort_order": 9},
        {"id": gen_id(), "name": "Mainor Lopez", "positions": [{"position_name": "Busser"}], "sort_order": 10},
        {"id": gen_id(), "name": "Chris Rivera", "positions": [{"position_name": "Busser"}], "sort_order": 11},
        {"id": gen_id(), "name": "Kenny Olivares Celin", "positions": [{"position_name": "Busser"}], "sort_order": 12},
        {"id": gen_id(), "name": "Hirinio Nazario Jr", "positions": [{"position_name": "Barback"}], "sort_order": 13},
        {"id": gen_id(), "name": "Myrto Hatzikyriakou", "positions": [{"position_name": "Host"}], "sort_order": 14},
        {"id": gen_id(), "name": "Sevasti Panopoulos", "positions": [{"position_name": "Host"}], "sort_order": 15},
        {"id": gen_id(), "name": "Elvira Espinobarros", "positions": [{"position_name": "Kitchen"}], "sort_order": 0},
        {"id": gen_id(), "name": "Jessica Hernandez", "positions": [{"position_name": "Kitchen"}], "sort_order": 1},
        {"id": gen_id(), "name": "Sylvia Garcia", "positions": [{"position_name": "Kitchen"}], "sort_order": 2},
        {"id": gen_id(), "name": "Abdil Izai Romeo", "positions": [{"position_name": "Kitchen"}], "sort_order": 3},
        {"id": gen_id(), "name": "Beltran Isael", "positions": [{"position_name": "Kitchen"}], "sort_order": 4},
        {"id": gen_id(), "name": "Maria Castro", "positions": [{"position_name": "Kitchen"}], "sort_order": 5},
        {"id": gen_id(), "name": "Soc Luis", "positions": [{"position_name": "Dishwasher"}], "sort_order": 6},
        {"id": gen_id(), "name": "Quino Eleazir", "positions": [{"position_name": "Dishwasher"}], "sort_order": 7},
        {"id": gen_id(), "name": "Gerson Gomez", "positions": [{"position_name": "Cleaner"}], "sort_order": 8},
        {"id": gen_id(), "name": "Edgar", "positions": [{"position_name": "Chef"}], "sort_order": 9},
        {"id": gen_id(), "name": "Joseph", "positions": [{"position_name": "Chef"}], "sort_order": 10},
    ]

    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(POS_FILE, "w") as f:
        json.dump(positions, f, indent=2)
    with open(EMP_FILE, "w") as f:
        json.dump(employees, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
#  ACCESS CONTROL CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
# Set these to match your admin server:
ACCESS_SERVER_URL = "http://localhost:5050"
ACCESS_API_KEY    = ""   # paste the API key from admin_server.py here

# Set to False to disable access control entirely (run app freely)
ACCESS_CONTROL_ENABLED = True


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    seed()

    if ACCESS_CONTROL_ENABLED and ACCESS_API_KEY:
        from access_control import AccessGate, check_access

        root = tk.Tk()
        root.title(APP_TITLE)
        root.configure(bg="#0F172A")
        root.minsize(MIN_W, MIN_H)
        root.geometry("1160x820")

        def launch_app():
            root.destroy()
            app = App()
            app.mainloop()

        gate = AccessGate(root, ACCESS_SERVER_URL, ACCESS_API_KEY, launch_app)
        root.mainloop()
    else:
        app = App()
        app.mainloop()
