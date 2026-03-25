# Stamhad Payroll — Design System & GUI Template

**v1.2 — Python tkinter Desktop Application — Cross-platform (Windows / macOS / Linux)**

---

## 1. Application Architecture

- **Framework:** Python 3 + tkinter (standard library GUI)
- **Data:** Firebase Realtime Database (REST API) with offline-first local JSON cache
- **Build:** PyInstaller (.exe for Windows, .app/.dmg for macOS)
- **CI/CD:** GitHub Actions triggered by git tag push (v*.*.*)
- **Min Window Size:** 1040 × 740 pixels

---

## 2. Colour Palette

### Core Backgrounds

| Swatch | Hex | Variable | Usage |
|--------|-----|----------|-------|
| 🟦 | `#F0F2F5` | `BG_PAGE` | Page/screen background |
| ⬜ | `#FFFFFF` | `BG_CARD` | Cards, inputs, modals |
| 🟫 | `#1B2A4A` | `BG_NAV` | Navigation bar, dark panels |
| ⬜ | `#FFFFFF` | `BG_INPUT` | Input fields |

### Borders

| Hex | Variable | Usage |
|-----|----------|-------|
| `#E5E7EB` | `BORDER` | Default card/table borders |
| `#F3F4F6` | `BORDER_LT` | Light row separators |
| `#4F46E5` | `BORDER_FOCUS` | Focused input border |

### Text Colors

| Hex | Variable | Usage |
|-----|----------|-------|
| `#1C1C1E` | `FG` | Primary text (headings, body) |
| `#6B7280` | `FG_SEC` | Secondary text (labels, hints) |
| `#374151` | `FG_HDR` | Table headers, cancel button text |

### Brand / Accent Colors

| Hex | Variable | Usage |
|-----|----------|-------|
| `#4F46E5` | `ACCENT` | Primary accent (buttons, links, nav active) |
| `#4338CA` | `ACCENT_HV` | Accent hover state |
| `#10B981` | `SUCCESS` | Success states, tip totals |
| `#059669` | `SUCCESS_HV` | Success hover |
| `#D1FAE5` | `SUCCESS_BG` | Success banner background |
| `#065F46` | `SUCCESS_FG` | Success banner text |
| `#EF4444` | `DANGER` | Danger buttons, delete, labor cost |
| `#DC2626` | `DANGER_HV` | Danger hover |
| `#0891B2` | `EXPORT_BG` | Export buttons (teal) |
| `#0E7490` | `EXPORT_HV` | Export hover |
| `#F59E0B` | `WARN_BORD` | Warning border/icon, warning buttons |
| `#FEF3C7` | `WARN_BG` | Warning banner background |
| `#92400E` | `WARN_FG` | Warning banner text |
| `#D97706` | `WARN_HV` | Warning button hover |

### Department & Shift Colors

| Hex | Variable | Text Color | Usage |
|-----|----------|------------|-------|
| `#3B82F6` | `FOH_BG` | `#FFFFFF` | FOH pill background |
| `#F97316` | `BOH_BG` | `#FFFFFF` | BOH pill background |
| `#FCD34D` | Morning | `#78350F` | Morning shift pill |
| `#34D399` | Brunch | `#064E3B` | Brunch shift pill |
| `#818CF8` | Dinner | `#312E81` | Dinner shift pill |

### Table Row Alternation

| Hex | Variable | Usage |
|-----|----------|-------|
| `#FFFFFF` | `ROW_A` | Even rows |
| `#EEF1F4` | `ROW_B` | Odd rows |

### Nav Bar Specific Colors

| Hex | Usage |
|-----|-------|
| `#7EB8FF` | App name text in nav bar |
| `#94A3B8` | Inactive nav items |
| `#2D4A7A` | Nav item hover background |
| `#FFD580` | Date display text (gold) |
| `#B0C4DE` | Date navigation arrows |

---

## 3. Typography

**Platform-native fonts:**

```
macOS:   "Helvetica Neue"
Linux:   "Ubuntu"
Windows: "Segoe UI"
```

### Font Size Scale

| Size | Weight | Usage |
|------|--------|-------|
| 18pt | Bold | Page titles (Week View, Payroll Report) |
| 16pt | Bold | Section headers (Who Worked Monday?) |
| 15pt | Bold | Nav bar app name |
| 14pt | Bold | Weekly labor total, section headings |
| 13pt | Bold | Card titles, table section headers |
| 12pt | Bold | Employee names, checkbox labels |
| 12pt | Normal | Input text, entry fields |
| 11pt | Bold | Nav items, tab labels, button labels, column headers |
| 11pt | Normal | Footer info text |
| 10pt | Bold | Table data, cell labels, edit links |
| 9pt | Bold | Department pills (FOH/BOH) |
| 8pt | Bold | Shift pills (Morning/Brunch/Dinner) |

---

## 4. Component Library

### Btn (Custom Button Widget)

Label-based button that renders background colors correctly on macOS. Uses hover transitions.

| Style | Background | Text | Hover | Usage |
|-------|-----------|------|-------|-------|
| `primary` | `#4F46E5` | `#FFFFFF` | `#4338CA` | Save, main actions |
| `success` | `#10B981` | `#FFFFFF` | `#059669` | Confirm, positive actions |
| `danger` | `#EF4444` | `#FFFFFF` | `#DC2626` | Delete, destructive actions |
| `export` | `#0891B2` | `#FFFFFF` | `#0E7490` | Export CSV, PDF buttons |
| `warning` | `#F59E0B` | `#FFFFFF` | `#D97706` | Add Shift, caution actions |
| `cancel` | `#FFFFFF` | `#374151` | `#E5E7EB` | Cancel, secondary actions |
| `ghost` | `#FFFFFF` | `#374151` | `#E5E7EB` | Prev/Next Week, subtle actions |
| `outline` | `#FFFFFF` | `#4F46E5` | `#EEF2FF` | Outlined accent buttons |

**Spec:** font 11pt bold, padx=16, pady=8, cursor=hand2, highlightthickness=1

### Inp (Input Field)

Styled `tk.Entry`: white bg, flat relief, 12pt font, 1px border (`#E5E7EB`), focus border (`#4F46E5`).

### Card

White container frame with 1px border (`#E5E7EB`), padx=16, pady=12.

### SectionBar

Colored left accent bar (4px wide) + bold 14pt section title. Used for FOH/BOH section dividers.

### DeptPill

Small department badge. FOH = `#3B82F6` bg / white text. BOH = `#F97316` bg / white text. Font 9pt bold, padx=5, pady=1.

### ShiftPill

Small shift badge. Morning = `#FCD34D` bg / `#78350F` text. Brunch = `#34D399` bg / `#064E3B` text. Dinner = `#818CF8` bg / `#312E81` text. Font 8pt bold, padx=4, pady=1.

### ScrollFrame

Scrollable container using Canvas + Scrollbar. Supports mousewheel on macOS, Windows, and Linux. Used for all pages.

### Toast (Notification)

Floating notification at top-center. Green success background (`#D1FAE5`, text `#065F46`). Shows for 3 seconds. Font 12pt bold, padx=20, pady=10, placed at relx=0.5, y=56.

---

## 5. Layout Structure

### Navigation Bar (52px fixed height)

```
┌──────────────────────────────────────────────────────────────────────┐
│  [Icon]  Stamhad Payroll    Today  Week View  Employees  ...   ◀ Mar 19 ▶  │
│  32px    #7EB8FF 15pt bold  #94A3B8 inactive / #4F46E5 active  #FFD580     │
└──────────────────────────────────────────────────────────────────────┘
Background: #1B2A4A    Height: 52px    Nav hover: #2D4A7A
```

### Today Page (Tab System)

```
┌─ Tab Bar ──────────────────────────────────────────────────────────┐
│  [👥 Employees]  [⏱ Hours]  [💰 Tips]           [📥 Import from Toast] │
│  Active: ACCENT bg + white text                  Ghost button right │
│  Inactive: white bg + #374151 text                                  │
│  11pt bold, padx=16, pady=8, 1px solid border                      │
└────────────────────────────────────────────────────────────────────┘

┌─ Footer (fixed bottom) ────────────────────────────────────────────┐
│  Employees: 12  |  Tip Input Total: $1,234.00         [✓ Save Day] │
│  FG_SEC 11pt                                          primary btn   │
└────────────────────────────────────────────────────────────────────┘
```

### Week View Grid

```
┌─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┐
│   Mon   │   Tue   │   Wed   │   Thu   │   Fri   │   Sat   │   Sun   │
│ Mar 09  │ Mar 10  │ Mar 11  │ Mar 12  │ Mar 13  │ Mar 14  │ Mar 15  │
├─────────┼─────────┼─────────┼─────────┼─────────┼─────────┼─────────┤
│ ⏱✓ 💰✓ │ ⏱✓ 💰✓ │ ⏱✓ 💰⚠ │ ⏱⚠ 💰⚠ │         │         │         │
│ 11 emps │ 9 emps  │ 8 emps  │ 10 emps │ No      │         │         │
│ M:1|D:10│ M:1|D:7 │ M:1|D:6 │ M:1|D:9 │ shifts  │         │         │
│ $258.38 │ $512.07 │ $139.62 │$1023.10 │         │         │         │
│ 56.1 hrs│ 58.8 hrs│ 42.9 hrs│ 65.8 hrs│         │         │         │
│💸$922.53│💸$790.46│💸$647.84│💸$1103  │         │         │         │
└─────────┴─────────┴─────────┴─────────┴─────────┴─────────┴─────────┘
Column headers: BG_NAV, white text 10pt bold
Day cards: white bg, clickable (cursor=hand2)
Today's column: 2px ACCENT border
Status: ⏱✓/⚠ for hours, 💰✓/⚠ for tips (green SUCCESS / yellow WARN_BORD)
```

### Warning Banner

```
┌────────────────────────────────────────────────────────────────┐
│ ▌  Editing saved entry for Thursday, Mar 12                   │
│ 4px #F59E0B bar    bg=#FEF3C7   text=#92400E  12pt bold      │
└────────────────────────────────────────────────────────────────┘
```

---

## 6. Data Architecture

### Offline-First Pattern

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  In-Memory   │ ──▶ │  Disk Cache  │ ──▶ │   Firebase   │
│    Cache     │     │  (JSON file) │     │    Cloud     │
└──────────────┘     └──────────────┘     └──────────────┘
     Read first       Persist on save      Sync every 15s
```

- On login: bulk download all data from Firebase → local cache
- On save: update cache + CSV + try immediate Firebase sync, queue dirty on failure
- Background sync every 15 seconds processes dirty queue (`pending_sync.json`)
- Smart merge: local pending data preserved over Firebase data on download

### Key Files

```
config/firebase_cache.json   — Full local mirror of Firebase data
config/pending_sync.json     — Persistent dirty queue (survives restart)
config/employees.json        — Employee list with positions
config/positions.json        — Position definitions with wages
week_YYYY-MM-DD/             — Weekly CSV files (foh_hours, boh_hours, weekly_tips)
```

---

## 7. Icon & Branding System

```
icons/png/icon_dark_64.png       — Nav bar (subsampled to 32px)
icons/png/icon_dark_128.png      — Window icon (macOS/Linux iconphoto)
icons/png/logo_main_120.png      — Login screen, splash screen
icons/stamhad_payroll_icon_dark.ico — Windows taskbar/EXE (multi-res: 256,128,64,48,32,16)
```

Windows: `.ico` via `iconbitmap()`. macOS/Linux: PNG via `iconphoto()`.

---

## 8. Login & Splash Screens

### Login Window

- **Size:** 440×580, non-resizable
- **Background:** `#F1F5F9`
- **Card:** centered white card containing:
  - 64px app icon + "Stamhad Payroll" title + "by Stamhad Software" subtitle
  - Email + Password inputs (flat, 1px border, focus highlight)
  - Remember Me checkbox + Sign In primary button
  - Support email link at bottom

### Auto-Login Splash

- **Size:** 340×240, non-resizable
- Same icon + text pattern, shows "Signing in..." while re-authenticating

---

## 9. Quick-Start Code Template

Copy this skeleton to bootstrap a new app with the same look and feel:

```python
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import platform

# ── Platform font ──────────────────────────────────────────────
IS_MAC = platform.system() == "Darwin"
FONT = ("Helvetica Neue" if IS_MAC
        else ("Ubuntu" if platform.system() == "Linux" else "Segoe UI"))

# ── Colour Palette ─────────────────────────────────────────────
BG_PAGE      = "#F0F2F5"
BG_CARD      = "#FFFFFF"
BG_NAV       = "#1B2A4A"
BG_INPUT     = "#FFFFFF"
BORDER       = "#E5E7EB"
BORDER_LT    = "#F3F4F6"
BORDER_FOCUS = "#4F46E5"

FG           = "#1C1C1E"
FG_SEC       = "#6B7280"
FG_HDR       = "#374151"

ACCENT       = "#4F46E5"
ACCENT_HV    = "#4338CA"
SUCCESS      = "#10B981"
SUCCESS_HV   = "#059669"
SUCCESS_BG   = "#D1FAE5"
SUCCESS_FG   = "#065F46"
DANGER       = "#EF4444"
DANGER_HV    = "#DC2626"
EXPORT_BG    = "#0891B2"
EXPORT_HV    = "#0E7490"
WARN_BG      = "#FEF3C7"
WARN_FG      = "#92400E"
WARN_BORD    = "#F59E0B"
WARN_HV      = "#D97706"
CANCEL_BG    = "#FFFFFF"
CANCEL_FG    = "#374151"
CANCEL_BD    = "#D1D5DB"
CANCEL_HV    = "#E5E7EB"

FOH_BG       = "#3B82F6"
FOH_FG       = "#FFFFFF"
BOH_BG       = "#F97316"
BOH_FG       = "#FFFFFF"

ROW_A        = "#FFFFFF"
ROW_B        = "#EEF1F4"


# ── Styled Button ──────────────────────────────────────────────
class Btn(tk.Frame):
    STYLES = {
        "primary":  (ACCENT,    "#FFFFFF", ACCENT_HV),
        "success":  (SUCCESS,   "#FFFFFF", SUCCESS_HV),
        "danger":   (DANGER,    "#FFFFFF", DANGER_HV),
        "export":   (EXPORT_BG, "#FFFFFF", EXPORT_HV),
        "cancel":   ("#FFFFFF", "#374151", "#E5E7EB"),
        "warning":  (WARN_BORD, "#FFFFFF", WARN_HV),
        "ghost":    ("#FFFFFF", "#374151", "#E5E7EB"),
        "outline":  ("#FFFFFF", ACCENT,   "#EEF2FF"),
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


# ── Styled Input ───────────────────────────────────────────────
class Inp(tk.Entry):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG_INPUT, fg=FG, insertbackground=FG,
                         relief="flat", font=(FONT, 12), bd=0,
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=BORDER_FOCUS, **kw)


# ── Card Container ─────────────────────────────────────────────
class Card(tk.Frame):
    def __init__(self, parent, bg=BG_CARD, **kw):
        super().__init__(parent, bg=bg, highlightbackground=BORDER,
                         highlightthickness=1, padx=16, pady=12, **kw)


# ── Section Bar ────────────────────────────────────────────────
class SectionBar(tk.Frame):
    def __init__(self, parent, text, color=ACCENT, bg=BG_PAGE):
        super().__init__(parent, bg=bg)
        tk.Frame(self, bg=color, width=4).pack(side="left", fill="y", padx=(0, 10))
        tk.Label(self, text=text, bg=bg, fg=FG,
                 font=(FONT, 14, "bold")).pack(side="left")


# ── App Skeleton ───────────────────────────────────────────────
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("My App")
        self.configure(bg=BG_PAGE)
        self.minsize(1040, 740)
        self._build_nav()

        self.main = tk.Frame(self, bg=BG_PAGE)
        self.main.pack(fill="both", expand=True)

    def _build_nav(self):
        nav = tk.Frame(self, bg=BG_NAV, height=52)
        nav.pack(side="top", fill="x")
        nav.pack_propagate(False)

        tk.Label(nav, text="My App", bg=BG_NAV, fg="#7EB8FF",
                 font=(FONT, 15, "bold")).pack(side="left", padx=(12, 24))

        for lbl in ["Dashboard", "Settings"]:
            b = tk.Label(nav, text=lbl, bg=BG_NAV, fg="#94A3B8",
                         font=(FONT, 11, "bold"), padx=14, pady=6,
                         cursor="hand2")
            b.pack(side="left", padx=2, pady=8)


if __name__ == "__main__":
    app = App()
    app.mainloop()
```

---

*Stamhad Software — Design System Template v1.2*
