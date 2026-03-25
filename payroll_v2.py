"""
Stamhad Payroll — Payroll V2: Tax Integration, Per-Employee Tax Toggle & Export
Extends the main App class. Does NOT modify payroll_app.py.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv, json, io, platform
from datetime import date, datetime, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                Paragraph, Spacer, PageBreak, Image as RLImage)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# Import main app objects
from payroll_app import (
    App, Btn, Inp, Card, DeptPill, SectionBar, ScrollFrame, DataManager,
    BG_PAGE, BG_CARD, BG_NAV, BG_INPUT, BORDER, BORDER_LT, BORDER_FOCUS,
    FG, FG_SEC, FG_HDR, ACCENT, ACCENT_HV, SUCCESS, SUCCESS_BG, SUCCESS_FG,
    DANGER, WARN_BG, WARN_FG, WARN_BORD, EXPORT_BG, TOTAL_LABOR_BG,
    FOH_BG, BOH_BG, ROW_A, ROW_B, FONT, SHIFTS, DAYS,
    fmt, safe_float, monday_of, week_dir, gen_id,
)

import tax_calculator as taxcalc

BASE_DIR = Path(__file__).parent
_PDF_LOGO = BASE_DIR / "icons" / "png" / "icon_light_64.png"

def _pdf_logo_element():
    """Return a ReportLab Image of the light icon for PDFs, or None."""
    try:
        if _PDF_LOGO.exists():
            return RLImage(str(_PDF_LOGO), width=32, height=32)
    except Exception:
        pass
    return None

# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
FED_FILING_OPTIONS = [
    "Single", "Married Filing Jointly",
    "Married Filing Separately", "Head of Household",
]
W4_VERSION_OPTIONS = ["2020+ New W-4", "Pre-2020 Old W-4"]
NY_FILING_OPTIONS = ["Single", "Married", "Head of Household"]

SIDEBAR_W = 280
GREEN_DOT = "#10B981"
YELLOW_DOT = "#F59E0B"
GREY_DOT = "#9CA3AF"


# ═══════════════════════════════════════════════════════════════════════════════
#  EMPLOYEE EDIT MODAL — Tax Info Tab
# ═══════════════════════════════════════════════════════════════════════════════

def _emp_dlg_v2(app, emp=None, open_tax_tab=False):
    """Replacement employee edit modal with 2 tabs: General + Tax Info."""
    win = tk.Toplevel(app)
    win.title("Edit Employee" if emp else "New Employee")
    win.configure(bg=BG_CARD)
    win.geometry("600x720")
    win.transient(app)
    win.grab_set()

    tk.Label(win, text="Edit Employee" if emp else "New Employee",
             bg=BG_CARD, fg=ACCENT, font=(FONT, 16, "bold")).pack(pady=(16, 8))

    # ── Tab bar ───────────────────────────────────────────────────────────
    tab_bar = tk.Frame(win, bg=BG_CARD)
    tab_bar.pack(fill="x", padx=20)
    tab_btns = {}
    tab_frames = {}

    content_area = tk.Frame(win, bg=BG_CARD)
    content_area.pack(fill="both", expand=True)

    for tab_name in ["\U0001F464 General Info", "\U0001F4B0 Tax Info", "\u2702 % Reduction"]:
        f = tk.Frame(content_area, bg=BG_CARD)
        tab_frames[tab_name] = f

        lbl = tk.Label(tab_bar, text=f"  {tab_name}  ", bg="#FFFFFF", fg="#374151",
                       font=(FONT, 11, "bold"), padx=14, pady=6, cursor="hand2",
                       relief="solid", bd=1)
        lbl.pack(side="left", padx=4)
        tab_btns[tab_name] = lbl

    active_tab = {"current": None}

    def switch_tab(name):
        for n, f in tab_frames.items():
            f.pack_forget()
        tab_frames[name].pack(fill="both", expand=True)
        for n, b in tab_btns.items():
            if n == name:
                b.config(bg=ACCENT, fg="#FFFFFF")
            else:
                b.config(bg="#FFFFFF", fg="#374151")
        active_tab["current"] = name

    for n, b in tab_btns.items():
        b.bind("<Button-1>", lambda e, nm=n: switch_tab(nm))

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 1: General Info (same as original _emp_dlg)
    # ══════════════════════════════════════════════════════════════════════
    gen_frame = tab_frames["\U0001F464 General Info"]

    gen_scroll = ScrollFrame(gen_frame, bg=BG_CARD)
    gen_scroll.pack(fill="both", expand=True)

    tk.Label(gen_scroll, text="Full Name", bg=BG_CARD, fg=FG_SEC,
             font=(FONT, 11)).pack(fill="x", padx=28, pady=(12, 0))
    ne = Inp(gen_scroll, width=30)
    ne.pack(fill="x", padx=28, pady=(0, 8))
    if emp:
        ne.insert(0, emp["name"])

    if emp:
        tk.Label(gen_scroll, text=f"ID: {emp['id']}", bg=BG_CARD, fg=FG_SEC,
                 font=("Consolas", 11)).pack(padx=28, anchor="w")

    tk.Label(gen_scroll, text="Assigned Positions",
             bg=BG_CARD, fg=ACCENT, font=(FONT, 12, "bold")).pack(
        fill="x", padx=28, pady=(12, 6))

    pf = tk.Frame(gen_scroll, bg=BG_CARD)
    pf.pack(fill="both", expand=True, padx=28)
    existing_names = set()
    if emp:
        existing_names = {a["position_name"] for a in emp.get("positions", [])}

    pvars = []
    for pos in app.dm.positions:
        f = tk.Frame(pf, bg=BG_CARD)
        f.pack(fill="x", pady=3)
        v = tk.BooleanVar(value=pos["name"] in existing_names)
        tk.Checkbutton(f, text=pos["name"], variable=v, bg=BG_CARD, fg=FG,
                       selectcolor=BG_INPUT, activebackground=BG_CARD,
                       font=(FONT, 12),
                       command=lambda: _update_main_pos_dropdown()).pack(side="left")
        DeptPill(f, pos.get("department", "FOH")).pack(side="left", padx=8)
        tk.Label(f, text=f'({fmt(pos.get("hourly_wage", 0))}/hr)',
                 bg=BG_CARD, fg=FG_SEC, font=(FONT, 11)).pack(side="left", padx=4)
        pvars.append((v, pos["name"]))

    # ── Main (default) position selector ────────────────────────────────
    main_pos_frame = tk.Frame(gen_scroll, bg=BG_CARD)
    main_pos_frame.pack(fill="x", padx=28, pady=(12, 6))
    tk.Label(main_pos_frame, text="Main Position",
             bg=BG_CARD, fg=ACCENT, font=(FONT, 12, "bold")).pack(anchor="w")
    tk.Label(main_pos_frame, text="Default position used when adding hours",
             bg=BG_CARD, fg=FG_SEC, font=(FONT, 10)).pack(anchor="w")
    main_pos_cb = ttk.Combobox(main_pos_frame, state="readonly", width=25,
                               font=(FONT, 11))
    main_pos_cb.pack(anchor="w", pady=(4, 0))

    current_main = emp.get("main_position", "") if emp else ""

    def _update_main_pos_dropdown():
        checked = [pn for v, pn in pvars if v.get()]
        main_pos_cb["values"] = checked
        cur = main_pos_cb.get()
        if not checked:
            main_pos_cb.set("")
        elif len(checked) == 1:
            main_pos_cb.set(checked[0])
        elif cur not in checked:
            main_pos_cb.set(checked[0])

    _update_main_pos_dropdown()
    if current_main and current_main in [pn for v, pn in pvars if v.get()]:
        main_pos_cb.set(current_main)
    elif main_pos_cb["values"]:
        main_pos_cb.set(main_pos_cb["values"][0] if main_pos_cb["values"] else "")

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 2: Tax Info
    # ══════════════════════════════════════════════════════════════════════
    tax_frame = tab_frames["\U0001F4B0 Tax Info"]
    tax_scroll = ScrollFrame(tax_frame, bg=BG_CARD)
    tax_scroll.pack(fill="both", expand=True)

    tax_info = emp.get("tax_info", {}) if emp else {}

    # ── Toggle ────────────────────────────────────────────────────────────
    toggle_card = tk.Frame(tax_scroll, bg="#EEF2FF", highlightbackground=ACCENT,
                           highlightthickness=1, padx=16, pady=12)
    toggle_card.pack(fill="x", padx=20, pady=(12, 8))

    tk.Label(toggle_card, text="Include taxes in payroll for this employee?",
             bg="#EEF2FF", fg=FG, font=(FONT, 12, "bold")).pack(anchor="w")

    tax_enabled_var = tk.BooleanVar(value=tax_info.get("tax_enabled", False))

    toggle_row = tk.Frame(toggle_card, bg="#EEF2FF")
    toggle_row.pack(fill="x", pady=(6, 4))
    toggle_lbl = tk.Label(toggle_row, text="", bg="#EEF2FF", fg=FG,
                          font=(FONT, 13, "bold"), cursor="hand2", padx=8)
    toggle_lbl.pack(side="left")

    tk.Label(toggle_card, text="OFF = Gross pay only  |  ON = Full tax breakdown",
             bg="#EEF2FF", fg=FG_SEC, font=(FONT, 10)).pack(anchor="w")

    # Container for all tax fields
    tax_fields_container = tk.Frame(tax_scroll, bg=BG_CARD)
    tax_fields_container.pack(fill="x", padx=20, pady=4)

    disabled_overlay_lbl = tk.Label(tax_fields_container,
        text="Enable tax calculation above to fill in\nthis employee's tax information",
        bg=BG_CARD, fg=FG_SEC, font=(FONT, 12), justify="center")

    # Tax field widgets (will be populated)
    tax_widgets = {}

    def build_tax_fields():
        for w in tax_fields_container.winfo_children():
            w.destroy()
        tax_widgets.clear()  # clear refs to destroyed widgets

        enabled = tax_enabled_var.get()

        if not enabled:
            disabled_overlay_lbl = tk.Label(tax_fields_container,
                text="\u2139\uFE0F  Enable tax calculation above to fill in\n"
                     "this employee's tax information",
                bg="#F9FAFB", fg=FG_SEC, font=(FONT, 12), justify="center",
                pady=40)
            disabled_overlay_lbl.pack(fill="x", pady=20)
            return

        # ── Group 1: Federal (W-4) ───────────────────────────────────────
        SectionBar(tax_fields_container, "Federal (W-4)", color=ACCENT,
                   bg=BG_CARD).pack(fill="x", pady=(8, 4))

        fed_f = tk.Frame(tax_fields_container, bg=BG_CARD)
        fed_f.pack(fill="x", padx=8)

        tk.Label(fed_f, text="Federal Filing Status", bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 10)).pack(anchor="w", pady=(4, 0))
        fed_status_var = tk.StringVar(value=tax_info.get("federal_filing_status", "Single"))
        fed_cb = ttk.Combobox(fed_f, textvariable=fed_status_var,
                              values=FED_FILING_OPTIONS, state="readonly",
                              font=(FONT, 11), width=30)
        fed_cb.pack(fill="x", pady=(0, 6))
        tax_widgets["federal_filing_status"] = fed_status_var

        tk.Label(fed_f, text="W-4 Version", bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 10)).pack(anchor="w")
        w4_var = tk.StringVar(value=tax_info.get("w4_version", "2020+ New W-4"))
        w4_cb = ttk.Combobox(fed_f, textvariable=w4_var, values=W4_VERSION_OPTIONS,
                             state="readonly", font=(FONT, 11), width=30)
        w4_cb.pack(fill="x", pady=(0, 6))
        tax_widgets["w4_version"] = w4_var

        mj_var = tk.BooleanVar(value=tax_info.get("multiple_jobs", False))
        tk.Checkbutton(fed_f, text="Step 2: Multiple Jobs", variable=mj_var,
                       bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                       activebackground=BG_CARD, font=(FONT, 11)).pack(anchor="w", pady=2)
        tax_widgets["multiple_jobs"] = mj_var

        for key, label, default in [
            ("dependents_amount", "Step 3: Dependents Amount ($)", "0"),
            ("other_income", "Step 4a: Other Income ($)", "0"),
            ("deductions", "Step 4b: Deductions ($)", "0"),
            ("extra_withholding", "Additional Extra Withholding ($)", "0"),
        ]:
            tk.Label(fed_f, text=label, bg=BG_CARD, fg=FG_SEC,
                     font=(FONT, 10)).pack(anchor="w", pady=(4, 0))
            e = Inp(fed_f, width=20)
            e.pack(anchor="w", pady=(0, 4))
            e.insert(0, str(tax_info.get(key, default)))
            tax_widgets[key] = e

        exempt_fed_var = tk.BooleanVar(value=tax_info.get("exempt_federal", False))
        tk.Checkbutton(fed_f, text="Exempt from Federal Withholding",
                       variable=exempt_fed_var, bg=BG_CARD, fg=DANGER,
                       selectcolor=BG_INPUT, activebackground=BG_CARD,
                       font=(FONT, 11)).pack(anchor="w", pady=4)
        tax_widgets["exempt_federal"] = exempt_fed_var

        # ── Group 2: New York State ──────────────────────────────────────
        SectionBar(tax_fields_container, "New York State (IT-2104)",
                   color="#E67E22", bg=BG_CARD).pack(fill="x", pady=(12, 4))

        ny_f = tk.Frame(tax_fields_container, bg=BG_CARD)
        ny_f.pack(fill="x", padx=8)

        tk.Label(ny_f, text="NY Filing Status", bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 10)).pack(anchor="w", pady=(4, 0))
        ny_status_var = tk.StringVar(value=tax_info.get("ny_filing_status", "Single"))
        ny_cb = ttk.Combobox(ny_f, textvariable=ny_status_var,
                             values=NY_FILING_OPTIONS, state="readonly",
                             font=(FONT, 11), width=30)
        ny_cb.pack(fill="x", pady=(0, 6))
        tax_widgets["ny_filing_status"] = ny_status_var

        tk.Label(ny_f, text="NY Additional Withholding ($)", bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 10)).pack(anchor="w")
        ny_extra_e = Inp(ny_f, width=20)
        ny_extra_e.pack(anchor="w", pady=(0, 6))
        ny_extra_e.insert(0, str(tax_info.get("ny_additional_withholding", "0")))
        tax_widgets["ny_additional_withholding"] = ny_extra_e

        nyc_var = tk.BooleanVar(value=tax_info.get("lives_in_nyc", False))
        tk.Checkbutton(ny_f, text="Lives in NYC (adds NYC local tax)",
                       variable=nyc_var, bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                       activebackground=BG_CARD, font=(FONT, 11)).pack(anchor="w", pady=2)
        tax_widgets["lives_in_nyc"] = nyc_var

        yonk_var = tk.BooleanVar(value=tax_info.get("lives_in_yonkers", False))
        tk.Checkbutton(ny_f, text="Lives in Yonkers (adds Yonkers surcharge)",
                       variable=yonk_var, bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                       activebackground=BG_CARD, font=(FONT, 11)).pack(anchor="w", pady=2)
        tax_widgets["lives_in_yonkers"] = yonk_var

        exempt_ny_var = tk.BooleanVar(value=tax_info.get("exempt_ny_state", False))
        tk.Checkbutton(ny_f, text="Exempt from NY State", variable=exempt_ny_var,
                       bg=BG_CARD, fg=DANGER, selectcolor=BG_INPUT,
                       activebackground=BG_CARD, font=(FONT, 11)).pack(anchor="w", pady=4)
        tax_widgets["exempt_ny_state"] = exempt_ny_var

        # ── Group 3: Status Indicators (live preview) ────────────────────
        SectionBar(tax_fields_container, "Estimated Weekly Deductions",
                   color=SUCCESS, bg=BG_CARD).pack(fill="x", pady=(12, 4))

        est_frame = tk.Frame(tax_fields_container, bg="#F9FAFB",
                             highlightbackground=BORDER, highlightthickness=1)
        est_frame.pack(fill="x", padx=8, pady=4)

        est_labels = {}
        for key, label in [
            ("federal", "Est. Weekly Federal:"),
            ("ny_state", "Est. Weekly NY State:"),
            ("fica", "Est. Weekly FICA:"),
            ("total", "Est. Weekly Total Deductions:"),
        ]:
            row = tk.Frame(est_frame, bg="#F9FAFB")
            row.pack(fill="x", padx=12, pady=2)
            tk.Label(row, text=label, bg="#F9FAFB", fg=FG_SEC,
                     font=(FONT, 10), width=28, anchor="w").pack(side="left")
            val_lbl = tk.Label(row, text="$0.00", bg="#F9FAFB", fg=FG,
                               font=(FONT, 10, "bold"))
            val_lbl.pack(side="left")
            est_labels[key] = val_lbl

        def update_estimates(*args):
            try:
                info = _collect_tax_info()
                info["tax_enabled"] = True
                result = taxcalc.estimate_weekly_from_fields(info)
                est_labels["federal"].config(text=fmt(result["federal_income_tax"]))
                est_labels["ny_state"].config(text=fmt(result["ny_state_income_tax"]))
                fica = result["social_security"] + result["medicare"]
                est_labels["fica"].config(text=fmt(fica))
                est_labels["total"].config(text=fmt(result["total_deductions"]),
                                           fg=DANGER)
            except Exception:
                pass

        # Bind trace to combobox vars
        for var_key in ["federal_filing_status", "ny_filing_status", "w4_version",
                        "multiple_jobs", "exempt_federal", "exempt_ny_state",
                        "lives_in_nyc", "lives_in_yonkers"]:
            w = tax_widgets.get(var_key)
            if isinstance(w, (tk.BooleanVar, tk.StringVar)):
                w.trace_add("write", update_estimates)

        # Initial estimate
        win.after(200, update_estimates)

    def _collect_tax_info():
        info = {"tax_enabled": tax_enabled_var.get()}
        for key, w in tax_widgets.items():
            if isinstance(w, tk.BooleanVar):
                info[key] = w.get()
            elif isinstance(w, tk.StringVar):
                info[key] = w.get()
            elif isinstance(w, tk.Entry):
                info[key] = w.get()
        return info

    def toggle_tax():
        new_val = not tax_enabled_var.get()
        tax_enabled_var.set(new_val)
        update_toggle_display()
        build_tax_fields()

    def update_toggle_display():
        if tax_enabled_var.get():
            toggle_lbl.config(text="\u2705  ON — Tax Calculation Enabled",
                              fg=SUCCESS)
        else:
            toggle_lbl.config(text="\u26AA  OFF — Gross Pay Only",
                              fg=FG_SEC)

    toggle_lbl.bind("<Button-1>", lambda e: toggle_tax())
    update_toggle_display()
    build_tax_fields()

    # ══════════════════════════════════════════════════════════════════════
    #  TAB 3: % Reduction (check cashing / payroll deduction)
    # ══════════════════════════════════════════════════════════════════════
    red_frame = tab_frames["\u2702 % Reduction"]
    red_scroll = ScrollFrame(red_frame, bg=BG_CARD)
    red_scroll.pack(fill="both", expand=True)

    red_info = emp.get("reduction", {}) if emp else {}

    # Toggle card
    red_toggle_card = tk.Frame(red_scroll, bg="#EEF2FF", highlightbackground=ACCENT,
                               highlightthickness=1, padx=16, pady=12)
    red_toggle_card.pack(fill="x", padx=20, pady=(12, 8))

    tk.Label(red_toggle_card, text="Apply a % reduction to this employee's check?",
             bg="#EEF2FF", fg=FG, font=(FONT, 12, "bold")).pack(anchor="w")

    red_enabled_var = tk.BooleanVar(value=red_info.get("enabled", False))

    red_toggle_row = tk.Frame(red_toggle_card, bg="#EEF2FF")
    red_toggle_row.pack(fill="x", pady=(6, 4))
    red_toggle_lbl = tk.Label(red_toggle_row, text="", bg="#EEF2FF",
                              font=(FONT, 13, "bold"), cursor="hand2", padx=8)
    red_toggle_lbl.pack(side="left")

    tk.Label(red_toggle_card, text="OFF = Full pay  |  ON = Deduct % from total compensation",
             bg="#EEF2FF", fg=FG_SEC, font=(FONT, 10)).pack(anchor="w")

    # Percentage input area
    red_fields_container = tk.Frame(red_scroll, bg=BG_CARD)
    red_fields_container.pack(fill="x", padx=20, pady=8)

    red_pct_entry = None  # will hold the Entry widget when enabled

    def build_red_fields():
        nonlocal red_pct_entry
        for w in red_fields_container.winfo_children():
            w.destroy()
        red_pct_entry = None

        if not red_enabled_var.get():
            tk.Label(red_fields_container,
                     text="\u2139\uFE0F  Enable reduction above to set the percentage",
                     bg="#F9FAFB", fg=FG_SEC, font=(FONT, 12), justify="center",
                     pady=40).pack(fill="x", pady=20)
            return

        card = tk.Frame(red_fields_container, bg=BG_CARD)
        card.pack(fill="x", pady=8)

        tk.Label(card, text="Reduction Percentage (%)", bg=BG_CARD, fg=FG,
                 font=(FONT, 12, "bold")).pack(anchor="w", pady=(4, 0))
        tk.Label(card, text="This percentage will be deducted from the employee's total pay",
                 bg=BG_CARD, fg=FG_SEC, font=(FONT, 10)).pack(anchor="w", pady=(0, 6))

        pct_row = tk.Frame(card, bg=BG_CARD)
        pct_row.pack(anchor="w")

        red_pct_entry = Inp(pct_row, width=8)
        red_pct_entry.pack(side="left")
        saved_pct = red_info.get("percentage", 10)
        red_pct_entry.insert(0, str(saved_pct))

        tk.Label(pct_row, text=" %", bg=BG_CARD, fg=FG,
                 font=(FONT, 14, "bold")).pack(side="left")

        # Preview
        preview_frame = tk.Frame(card, bg="#F9FAFB", highlightbackground=BORDER,
                                 highlightthickness=1)
        preview_frame.pack(fill="x", pady=(12, 4))
        tk.Label(preview_frame, text="\U0001F4CB Example:", bg="#F9FAFB", fg=FG_SEC,
                 font=(FONT, 10, "bold")).pack(anchor="w", padx=10, pady=(6, 2))
        tk.Label(preview_frame,
                 text=f"If total pay = $1,000 and reduction = {saved_pct}%\n"
                      f"Deduction = ${1000 * saved_pct / 100:.2f}  |  "
                      f"Net pay = ${1000 - 1000 * saved_pct / 100:.2f}",
                 bg="#F9FAFB", fg=FG, font=(FONT, 11), justify="left").pack(
            anchor="w", padx=10, pady=(0, 8))

    def toggle_red():
        new_val = not red_enabled_var.get()
        red_enabled_var.set(new_val)
        update_red_display()
        build_red_fields()

    def update_red_display():
        if red_enabled_var.get():
            red_toggle_lbl.config(text="\u2705  ON — Reduction Enabled", fg=SUCCESS)
        else:
            red_toggle_lbl.config(text="\u26AA  OFF — Full Pay", fg=FG_SEC)

    red_toggle_lbl.bind("<Button-1>", lambda e: toggle_red())
    update_red_display()
    build_red_fields()

    def _collect_reduction():
        info = {"enabled": red_enabled_var.get()}
        if red_enabled_var.get() and red_pct_entry:
            try:
                info["percentage"] = float(red_pct_entry.get())
            except (ValueError, tk.TclError):
                info["percentage"] = 10
        else:
            info["percentage"] = red_info.get("percentage", 10)
        return info

    # ── Warning label ─────────────────────────────────────────────────────
    warn_lbl = tk.Label(win, text="", bg=BG_CARD, fg=DANGER,
                        font=(FONT, 10, "bold"))
    warn_lbl.pack(fill="x", padx=28)

    # ── Save / Cancel ─────────────────────────────────────────────────────
    btn_frame = tk.Frame(win, bg=BG_CARD)
    btn_frame.pack(pady=12)

    def save():
        name = ne.get().strip()
        if not name:
            messagebox.showwarning("Missing", "Name required.", parent=win)
            return
        assigned = [{"position_name": pn} for v, pn in pvars if v.get()]
        if not assigned:
            messagebox.showwarning("Missing", "Assign at least one position.", parent=win)
            return

        ti = _collect_tax_info()
        if ti.get("tax_enabled"):
            fs = ti.get("federal_filing_status", "")
            if not fs:
                warn_lbl.config(text="\u26A0\uFE0F Filing status is required for tax calculation")
                return

        ri = _collect_reduction()

        main_pos = main_pos_cb.get().strip()
        if not main_pos and assigned:
            main_pos = assigned[0]["position_name"]

        if emp:
            emp["name"] = name
            emp["positions"] = assigned
            emp["main_position"] = main_pos
            emp["tax_info"] = ti
            emp["reduction"] = ri
        else:
            app.dm.employees.append({
                "id": gen_id(), "name": name,
                "positions": assigned, "main_position": main_pos,
                "sort_order": 9999,
                "tax_info": ti, "reduction": ri,
            })
        app.dm.save_emp()
        win.destroy()
        if hasattr(app, '_payroll_v2_active') and app._payroll_v2_active:
            app._clr()
            pg_payroll_v2(app)
        else:
            app._clr()
            app.pg_emps()
        app.toast.show("Employee updated successfully!")

    Btn(btn_frame, text="\u2713  Save", command=save, style="primary").pack(side="left", padx=8)
    Btn(btn_frame, text="Cancel", command=win.destroy, style="cancel").pack(side="left", padx=8)

    # Open to correct tab
    if open_tax_tab:
        switch_tab("\U0001F4B0 Tax Info")
    else:
        switch_tab("\U0001F464 General Info")


# ═══════════════════════════════════════════════════════════════════════════════
#  PAYROLL V2 SCREEN
# ═══════════════════════════════════════════════════════════════════════════════

def pg_payroll_v2(app):
    """Build the Payroll V2 screen with sidebar + detail panel."""
    try:
        _pg_payroll_v2_inner(app)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        err_lbl = tk.Label(app.main, text=f"Payroll V2 Error:\n{tb}",
                           bg=BG_PAGE, fg="#DC2626", font=("Consolas", 10),
                           justify="left", wraplength=700, anchor="nw")
        err_lbl.pack(fill="both", expand=True, padx=20, pady=20)


def _pg_payroll_v2_inner(app):
    """Inner implementation for Payroll V2 screen."""
    app._payroll_v2_active = True
    mon = app.cur_mon

    # Top bar
    top = tk.Frame(app.main, bg=BG_PAGE)
    top.pack(fill="x", padx=16, pady=(10, 4))

    tk.Label(top, text=f"Detailed payroll \u2014 Week of {mon.strftime('%b %d, %Y')}",
             bg=BG_PAGE, fg=FG, font=(FONT, 18, "bold")).pack(side="left")

    Btn(top, text="\U0001F4C4 Export All \u2192 PDF", style="export",
        command=lambda: _export_all_pdf(app, mon)).pack(side="right", padx=4)
    Btn(top, text="Switch to Classic Payroll", style="cancel",
        command=lambda: _switch_classic(app)).pack(side="right", padx=4)

    # Prev / Next Week navigation
    wnav = tk.Frame(app.main, bg=BG_PAGE)
    wnav.pack(fill="x", padx=16, pady=4)

    def _chg_wk_v2(d):
        app.sel_date += timedelta(days=d)
        app.cur_mon = monday_of(app.sel_date)
        app._upd_date()
        app._clr()
        pg_payroll_v2(app)

    Btn(wnav, text="\u2190 Prev Week", style="ghost",
        command=lambda: _chg_wk_v2(-7)).pack(side="left", padx=4)
    Btn(wnav, text="Next Week \u2192", style="ghost",
        command=lambda: _chg_wk_v2(7)).pack(side="left", padx=4)

    # Main split: sidebar + detail
    body = tk.Frame(app.main, bg=BG_PAGE)
    body.pack(fill="both", expand=True)

    # ── Sidebar ───────────────────────────────────────────────────────────
    sidebar_outer = tk.Frame(body, bg=BG_CARD, width=SIDEBAR_W,
                             highlightbackground=BORDER, highlightthickness=1)
    sidebar_outer.pack(side="left", fill="y", padx=(16, 0), pady=4)
    sidebar_outer.pack_propagate(False)

    sb_scroll = ScrollFrame(sidebar_outer, bg=BG_CARD)
    sb_scroll.pack(fill="both", expand=True)

    tk.Label(sb_scroll, text="Employees", bg=BG_CARD, fg=FG,
             font=(FONT, 13, "bold"), padx=12, pady=8).pack(anchor="w")

    # Detail panel
    detail_outer = tk.Frame(body, bg=BG_PAGE)
    detail_outer.pack(side="left", fill="both", expand=True, padx=8, pady=4)

    detail_container = tk.Frame(detail_outer, bg=BG_PAGE)
    detail_container.pack(fill="both", expand=True)

    # Get payroll data
    payroll = app.dm.gen_payroll(mon)
    emp_payroll = {r["emp_id"]: r for r in payroll}
    foh_list, boh_list = app.dm.sorted_employees()

    # Filter to employees who worked
    foh_worked = [e for e in foh_list if e["id"] in emp_payroll]
    boh_worked = [e for e in boh_list if e["id"] in emp_payroll]

    selected_emp = {"current": None}

    def select_emp(emp_obj):
        selected_emp["current"] = emp_obj
        _build_detail_panel(app, detail_container, emp_obj, emp_payroll, mon)
        # Update sidebar highlights
        for w_id, (lbl_w, eid) in sidebar_items.items():
            if eid == emp_obj["id"]:
                lbl_w.config(bg="#EEF2FF")
            else:
                lbl_w.config(bg=BG_CARD)

    sidebar_items = {}

    for dept_label, emp_list, color in [
        ("FOH", foh_worked, ACCENT), ("BOH", boh_worked, "#E67E22")]:

        if emp_list:
            tk.Label(sb_scroll, text=dept_label, bg=BG_CARD, fg=color,
                     font=(FONT, 10, "bold"), padx=12).pack(anchor="w", pady=(8, 2))

        for emp in emp_list:
            eid = emp["id"]
            ti = emp.get("tax_info", {})
            tax_on = ti.get("tax_enabled", False)

            if tax_on:
                fs = ti.get("federal_filing_status", "")
                dot_color = GREEN_DOT if fs else YELLOW_DOT
            else:
                dot_color = GREY_DOT

            row = tk.Frame(sb_scroll, bg=BG_CARD, cursor="hand2")
            row.pack(fill="x", padx=4, pady=1)

            dot = tk.Label(row, text="\u25CF", bg=BG_CARD, fg=dot_color,
                           font=(FONT, 10))
            dot.pack(side="left", padx=(8, 4))

            name_l = tk.Label(row, text=emp["name"], bg=BG_CARD, fg=FG,
                              font=(FONT, 11), cursor="hand2", anchor="w")
            name_l.pack(side="left", fill="x", expand=True, pady=6)

            dept = app.dm.emp_dept(emp)
            DeptPill(row, dept).pack(side="right", padx=6)

            for w in (row, dot, name_l):
                w.bind("<Button-1>", lambda e, em=emp: select_emp(em))

            sidebar_items[eid] = (row, eid)

    if not foh_worked and not boh_worked:
        tk.Label(sb_scroll, text="No shifts logged\nthis week.",
                 bg=BG_CARD, fg=FG_SEC, font=(FONT, 12), pady=30).pack()

    # Empty detail state
    tk.Label(detail_container, text="\u2190  Select an employee from the list",
             bg=BG_PAGE, fg=FG_SEC, font=(FONT, 14), pady=80).pack()

    # Auto-select first if available
    if foh_worked:
        select_emp(foh_worked[0])
    elif boh_worked:
        select_emp(boh_worked[0])


def _build_detail_panel(app, container, emp, emp_payroll, mon):
    """Build the right-side detail panel for a selected employee."""
    for w in container.winfo_children():
        w.destroy()
    try:
        _build_detail_inner(app, container, emp, emp_payroll, mon)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        err_lbl = tk.Label(container, text=f"Detail Error:\n{tb}",
                           bg=BG_PAGE, fg="#DC2626", font=("Consolas", 10),
                           justify="left", wraplength=600, anchor="nw")
        err_lbl.pack(fill="both", expand=True, padx=10, pady=10)


def _build_detail_inner(app, container, emp, emp_payroll, mon):
    scroll = ScrollFrame(container, bg=BG_PAGE)
    scroll.pack(fill="both", expand=True)

    pr = emp_payroll.get(emp["id"])
    if not pr:
        tk.Label(scroll, text="No payroll data for this employee.",
                 bg=BG_PAGE, fg=FG_SEC, font=(FONT, 14), pady=40).pack()
        return

    ti = emp.get("tax_info", {})
    tax_on = ti.get("tax_enabled", False)

    # Compute taxes
    gross = pr["total_compensation"]
    reg_wages = pr["regular_wages"]
    ot_wages = pr["overtime_wages"]
    tips = pr["total_tips"]
    gross_pay = round(reg_wages + ot_wages + tips, 2)

    ytd = taxcalc.compute_ytd_gross(BASE_DIR, emp["id"], mon)
    taxes = taxcalc.compute_weekly_taxes(gross_pay, ti, ytd_gross=ytd)

    # ── Header ────────────────────────────────────────────────────────────
    hdr = Card(scroll)
    hdr.pack(fill="x", padx=8, pady=(8, 4))

    hdr_left = tk.Frame(hdr, bg=BG_CARD)
    hdr_left.pack(side="left", fill="x", expand=True)

    name_row = tk.Frame(hdr_left, bg=BG_CARD)
    name_row.pack(fill="x")
    tk.Label(name_row, text=emp["name"], bg=BG_CARD, fg=FG,
             font=(FONT, 18, "bold")).pack(side="left")
    DeptPill(name_row, app.dm.emp_dept(emp)).pack(side="left", padx=8)

    tk.Label(hdr_left, text=f"Position(s): {pr['positions']}  |  "
             f"Days worked  |  ID: {emp['id']}",
             bg=BG_CARD, fg=FG_SEC, font=(FONT, 10)).pack(anchor="w", pady=(2, 0))

    Btn(hdr, text="\u270F\uFE0F Edit Tax Info", style="primary",
        command=lambda: _emp_dlg_v2(app, emp, open_tax_tab=True)).pack(
        side="right", padx=4)

    # ── Earnings Card ─────────────────────────────────────────────────────
    earn = Card(scroll)
    earn.pack(fill="x", padx=8, pady=4)

    tk.Label(earn, text="EARNINGS", bg=BG_CARD, fg=FG,
             font=(FONT, 13, "bold")).pack(anchor="w", pady=(0, 6))
    tk.Frame(earn, bg=BORDER, height=1).pack(fill="x")

    earn_items = [
        ("Regular Hours", f'{pr["regular_hours"]:.1f} hrs', fmt(reg_wages)),
        ("Overtime Hours", f'{pr["overtime_hours"]:.1f} hrs', fmt(ot_wages)),
        ("Floor Tips", "", fmt(tips)),  # tips combined for now
    ]
    for label, detail, amount in earn_items:
        row = tk.Frame(earn, bg=BG_CARD)
        row.pack(fill="x", pady=2)
        tk.Label(row, text=label, bg=BG_CARD, fg=FG, font=(FONT, 11),
                 width=20, anchor="w").pack(side="left")
        tk.Label(row, text=detail, bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 11)).pack(side="left", padx=8)
        tk.Label(row, text=amount, bg=BG_CARD, fg=FG,
                 font=(FONT, 11, "bold")).pack(side="right")

    tk.Frame(earn, bg=BORDER, height=1).pack(fill="x", pady=4)
    gross_row = tk.Frame(earn, bg=BG_CARD)
    gross_row.pack(fill="x")
    tk.Label(gross_row, text="Gross Pay", bg=BG_CARD, fg=FG,
             font=(FONT, 13, "bold")).pack(side="left")
    tk.Label(gross_row, text=fmt(gross_pay), bg=BG_CARD, fg=ACCENT,
             font=(FONT, 13, "bold")).pack(side="right")

    # ── Tax Deductions Card ───────────────────────────────────────────────
    if tax_on and taxes["tax_enabled"]:
        ded = Card(scroll)
        ded.pack(fill="x", padx=8, pady=4)

        tk.Label(ded, text="EMPLOYEE DEDUCTIONS", bg=BG_CARD, fg=FG,
                 font=(FONT, 13, "bold")).pack(anchor="w", pady=(0, 6))
        tk.Frame(ded, bg=BORDER, height=1).pack(fill="x")

        ded_items = [
            ("Federal Income Tax", taxes["federal_income_tax"]),
            ("Social Security (6.2%)", taxes["social_security"]),
            ("Medicare (1.45%)", taxes["medicare"]),
            ("NY State Income Tax", taxes["ny_state_income_tax"]),
            ("NY SDI", taxes["ny_sdi"]),
            ("NY Paid Family Leave", taxes["ny_paid_family_leave"]),
        ]
        if taxes["nyc_local_tax"] > 0:
            ded_items.append(("NYC Local Tax", taxes["nyc_local_tax"]))
        if taxes["yonkers_tax"] > 0:
            ded_items.append(("Yonkers Tax", taxes["yonkers_tax"]))

        for label, amount in ded_items:
            if amount == 0 and "NYC" in label:
                continue
            row = tk.Frame(ded, bg=BG_CARD)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, bg=BG_CARD, fg=FG,
                     font=(FONT, 11), anchor="w").pack(side="left")
            tk.Label(row, text=f"\u2212{fmt(amount)}", bg=BG_CARD, fg=DANGER,
                     font=(FONT, 11)).pack(side="right")

        tk.Frame(ded, bg=BORDER, height=1).pack(fill="x", pady=4)

        tot_row = tk.Frame(ded, bg=BG_CARD)
        tot_row.pack(fill="x")
        tk.Label(tot_row, text="Total Deductions", bg=BG_CARD, fg=FG,
                 font=(FONT, 12, "bold")).pack(side="left")
        tk.Label(tot_row, text=f"\u2212{fmt(taxes['total_deductions'])}",
                 bg=BG_CARD, fg=DANGER, font=(FONT, 12, "bold")).pack(side="right")

        net_row = tk.Frame(ded, bg="#F0FDF4")
        net_row.pack(fill="x", pady=(6, 0))
        tk.Label(net_row, text="NET PAY (Take-Home)", bg="#F0FDF4", fg=SUCCESS,
                 font=(FONT, 14, "bold"), padx=8, pady=6).pack(side="left")
        tk.Label(net_row, text=fmt(taxes["net_pay"]), bg="#F0FDF4", fg=SUCCESS,
                 font=(FONT, 14, "bold"), padx=8, pady=6).pack(side="right")
    else:
        # Tax disabled info card
        info_card = tk.Frame(scroll, bg="#F0F9FF", highlightbackground="#93C5FD",
                             highlightthickness=1, padx=16, pady=16)
        info_card.pack(fill="x", padx=8, pady=4)
        tk.Label(info_card, text="\u2139\uFE0F  Tax calculation is disabled\n"
                 "for this employee.\nGross pay only is shown.",
                 bg="#F0F9FF", fg=FG_SEC, font=(FONT, 12),
                 justify="left").pack(anchor="w")
        Btn(info_card, text="Enable Tax Calculation \u2192", style="primary",
            command=lambda: _emp_dlg_v2(app, emp, open_tax_tab=True)).pack(
            anchor="w", pady=(8, 0))

    # ── % Reduction Card ─────────────────────────────────────────────────
    red_data = emp.get("reduction", {})
    if red_data.get("enabled", False):
        red_pct = red_data.get("percentage", 10)
        # Compute net before reduction (after taxes if enabled, else gross)
        if tax_on and taxes["tax_enabled"]:
            pay_before_red = taxes["net_pay"]
        else:
            pay_before_red = gross_pay
        red_amount = round(pay_before_red * red_pct / 100, 2)
        pay_after_red = round(pay_before_red - red_amount, 2)

        red_card = Card(scroll)
        red_card.pack(fill="x", padx=8, pady=4)

        tk.Label(red_card, text=f"CHECK REDUCTION ({red_pct}%)", bg=BG_CARD, fg=FG,
                 font=(FONT, 13, "bold")).pack(anchor="w", pady=(0, 6))
        tk.Frame(red_card, bg=BORDER, height=1).pack(fill="x")

        r1 = tk.Frame(red_card, bg=BG_CARD)
        r1.pack(fill="x", pady=2)
        tk.Label(r1, text="Pay before reduction", bg=BG_CARD, fg=FG,
                 font=(FONT, 11)).pack(side="left")
        tk.Label(r1, text=fmt(pay_before_red), bg=BG_CARD, fg=FG,
                 font=(FONT, 11)).pack(side="right")

        r2 = tk.Frame(red_card, bg=BG_CARD)
        r2.pack(fill="x", pady=2)
        tk.Label(r2, text=f"Reduction ({red_pct}%)", bg=BG_CARD, fg=FG,
                 font=(FONT, 11)).pack(side="left")
        tk.Label(r2, text=f"\u2212{fmt(red_amount)}", bg=BG_CARD, fg=DANGER,
                 font=(FONT, 11)).pack(side="right")

        tk.Frame(red_card, bg=BORDER, height=1).pack(fill="x", pady=4)

        final_row = tk.Frame(red_card, bg="#FEF3C7")
        final_row.pack(fill="x", pady=(2, 0))
        tk.Label(final_row, text="FINAL PAY (After Reduction)", bg="#FEF3C7",
                 fg="#92400E", font=(FONT, 14, "bold"), padx=8, pady=6).pack(side="left")
        tk.Label(final_row, text=fmt(pay_after_red), bg="#FEF3C7",
                 fg="#92400E", font=(FONT, 14, "bold"), padx=8, pady=6).pack(side="right")

    # ── Employer Costs Card (always shown) ────────────────────────────────
    er_card = Card(scroll)
    er_card.pack(fill="x", padx=8, pady=4)

    tk.Label(er_card, text="EMPLOYER COSTS", bg=BG_CARD, fg=FG,
             font=(FONT, 13, "bold")).pack(anchor="w", pady=(0, 6))
    tk.Frame(er_card, bg=BORDER, height=1).pack(fill="x")

    er_items = [
        ("Employer Social Security (6.2%)", taxes["employer_ss"]),
        ("Employer Medicare (1.45%)", taxes["employer_medicare"]),
        ("FUTA", taxes["employer_futa"]),
    ]
    if taxes["employer_mctmt"] > 0:
        er_items.append(("NY MCTMT", taxes["employer_mctmt"]))

    for label, amount in er_items:
        row = tk.Frame(er_card, bg=BG_CARD)
        row.pack(fill="x", pady=1)
        tk.Label(row, text=label, bg=BG_CARD, fg=FG,
                 font=(FONT, 11), anchor="w").pack(side="left")
        tk.Label(row, text=fmt(amount), bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 11)).pack(side="right")

    tk.Frame(er_card, bg=BORDER, height=1).pack(fill="x", pady=4)

    er_tot = tk.Frame(er_card, bg=BG_CARD)
    er_tot.pack(fill="x")
    tk.Label(er_tot, text="Total Employer Tax", bg=BG_CARD, fg=FG,
             font=(FONT, 12, "bold")).pack(side="left")
    tk.Label(er_tot, text=fmt(taxes["total_employer_tax"]), bg=BG_CARD,
             fg=FG, font=(FONT, 12, "bold")).pack(side="right")

    labor_row = tk.Frame(er_card, bg=TOTAL_LABOR_BG)
    labor_row.pack(fill="x", pady=(6, 0))
    tk.Label(labor_row, text="TOTAL LABOR COST", bg=TOTAL_LABOR_BG, fg=DANGER,
             font=(FONT, 14, "bold"), padx=8, pady=6).pack(side="left")
    tk.Label(labor_row, text=fmt(taxes["total_labor_cost"]), bg=TOTAL_LABOR_BG,
             fg=DANGER, font=(FONT, 14, "bold"), padx=8, pady=6).pack(side="right")

    # ── Daily Breakdown Card ──────────────────────────────────────────────
    profile = app.dm.emp_weekly_profile(mon, emp["id"])
    day_data = profile.get("day_data", {})
    if day_data:
        daily_card = Card(scroll)
        daily_card.pack(fill="x", padx=8, pady=4)

        tk.Label(daily_card, text="DAILY BREAKDOWN", bg=BG_CARD, fg=FG,
                 font=(FONT, 13, "bold")).pack(anchor="w", pady=(0, 6))
        tk.Frame(daily_card, bg=BORDER, height=1).pack(fill="x")

        # Header row
        hdr_row = tk.Frame(daily_card, bg="#F3F4F6")
        hdr_row.pack(fill="x", pady=(4, 0))
        for col_text, col_w in [("Day", 12), ("Shift", 8), ("Position", 12),
                                ("Hours", 6), ("Wages", 8), ("Tips", 8)]:
            tk.Label(hdr_row, text=col_text, bg="#F3F4F6", fg=FG_SEC,
                     font=(FONT, 9, "bold"), width=col_w, anchor="w").pack(
                side="left", padx=2, pady=3)

        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                     "Friday", "Saturday", "Sunday"]
        row_i = 0
        for day_name in day_order:
            entries = day_data.get(day_name, [])
            if not entries:
                continue
            for entry in entries:
                bg = ROW_A if row_i % 2 == 0 else ROW_B
                r = tk.Frame(daily_card, bg=bg)
                r.pack(fill="x")
                tk.Label(r, text=day_name[:3], bg=bg, fg=FG,
                         font=(FONT, 10), width=12, anchor="w").pack(
                    side="left", padx=2, pady=2)
                tk.Label(r, text=entry.get("shift", ""), bg=bg, fg=FG_SEC,
                         font=(FONT, 10), width=8, anchor="w").pack(
                    side="left", padx=2)
                tk.Label(r, text=entry.get("position", ""), bg=bg, fg=FG,
                         font=(FONT, 10), width=12, anchor="w").pack(
                    side="left", padx=2)
                tk.Label(r, text=f'{entry.get("hours", 0):.1f}', bg=bg, fg=FG,
                         font=(FONT, 10), width=6, anchor="w").pack(
                    side="left", padx=2)
                tk.Label(r, text=fmt(entry.get("wages", 0)), bg=bg, fg=FG,
                         font=(FONT, 10), width=8, anchor="w").pack(
                    side="left", padx=2)
                tip_val = entry.get("total_tip", 0) or (
                    entry.get("floor_tip", 0) + entry.get("bar_tip", 0))
                tk.Label(r, text=fmt(tip_val), bg=bg, fg=SUCCESS,
                         font=(FONT, 10), width=8, anchor="w").pack(
                    side="left", padx=2)
                row_i += 1

        # Daily totals footer
        tk.Frame(daily_card, bg=BORDER, height=1).pack(fill="x", pady=(4, 0))
        foot = tk.Frame(daily_card, bg="#F0F9FF")
        foot.pack(fill="x")
        tk.Label(foot, text=f'{profile["days_worked"]} days', bg="#F0F9FF",
                 fg=FG, font=(FONT, 10, "bold"), width=12, anchor="w").pack(
            side="left", padx=2, pady=4)
        tk.Label(foot, text="", bg="#F0F9FF", width=8).pack(side="left", padx=2)
        tk.Label(foot, text="", bg="#F0F9FF", width=12).pack(side="left", padx=2)
        tk.Label(foot, text=f'{profile["total_hours"]:.1f}', bg="#F0F9FF",
                 fg=FG, font=(FONT, 10, "bold"), width=6, anchor="w").pack(
            side="left", padx=2)
        tk.Label(foot, text=fmt(profile["total_wages"]), bg="#F0F9FF",
                 fg=FG, font=(FONT, 10, "bold"), width=8, anchor="w").pack(
            side="left", padx=2)
        tk.Label(foot, text=fmt(profile["total_tips"]), bg="#F0F9FF",
                 fg=SUCCESS, font=(FONT, 10, "bold"), width=8, anchor="w").pack(
            side="left", padx=2)

    # ── Export buttons ────────────────────────────────────────────────────
    exp_row = tk.Frame(scroll, bg=BG_PAGE)
    exp_row.pack(fill="x", padx=8, pady=(12, 4))

    Btn(exp_row, text="\U0001F5A8 Print Weekly Details", style="primary",
        command=lambda: _print_weekly_details_pdf(app, emp, pr, taxes, profile, mon)).pack(
        side="left", padx=4)
    Btn(exp_row, text="\U0001F4C4 Export Payslip \u2014 PDF", style="export",
        command=lambda: _export_payslip_pdf(app, emp, pr, taxes, mon)).pack(
        side="left", padx=4)
    Btn(exp_row, text="\U0001F4CA Export Payslip \u2014 CSV", style="export",
        command=lambda: _export_payslip_csv(app, emp, pr, taxes, mon)).pack(
        side="left", padx=4)


# ═══════════════════════════════════════════════════════════════════════════════
#  PDF EXPORT — Weekly Details (Hours + Tips + Taxes)
# ═══════════════════════════════════════════════════════════════════════════════

def _print_weekly_details_pdf(app, emp, pr, taxes, profile, mon):
    """Generate a comprehensive PDF showing daily hours, tips, and tax summary."""
    end_date = mon + timedelta(days=6)
    folder = app.dm.ensure_wk(mon) / "payslips"
    folder.mkdir(exist_ok=True)

    safe_name = emp["name"].replace(" ", "_")
    filename = f"weekly_details_{safe_name}_{end_date.isoformat()}.pdf"
    filepath = folder / filename

    doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                            leftMargin=0.6 * inch, rightMargin=0.6 * inch)

    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle('WDTitle', parent=styles['Title'],
                                 fontSize=16, spaceAfter=4, alignment=1,
                                 textColor=colors.HexColor("#1B2A4A"))
    subtitle_style = ParagraphStyle('WDSub', parent=styles['Normal'],
                                    fontSize=10, alignment=1,
                                    textColor=colors.HexColor("#6B7280"))
    section_style = ParagraphStyle('WDSect', parent=styles['Heading3'],
                                   fontSize=12, spaceAfter=4, spaceBefore=10,
                                   textColor=colors.HexColor("#1B2A4A"))
    small_note = ParagraphStyle('WDNote', parent=styles['Normal'],
                                fontSize=7, textColor=colors.HexColor("#9CA3AF"),
                                alignment=1)

    # ── Header with logo ──────────────────────────────────────────────────
    logo_el = _pdf_logo_element()
    if logo_el:
        elements.append(logo_el)
        elements.append(Spacer(1, 4))
    _rest_name = getattr(app, '_logged_in_restaurant', 'My Restaurant') or 'My Restaurant'
    elements.append(Paragraph(_rest_name.upper(), title_style))
    elements.append(Paragraph("EMPLOYEE WEEKLY DETAILS", subtitle_style))
    elements.append(Spacer(1, 10))

    dept = pr.get("department", app.dm.emp_dept(emp))
    info_data = [
        ["Employee:", emp["name"], "Department:", dept],
        ["Position(s):", pr.get("positions", ""), "Employee ID:", emp["id"]],
        ["Pay Period:", f"{mon.strftime('%b %d')} \u2013 {end_date.strftime('%b %d, %Y')}",
         "Days Worked:", str(profile.get("days_worked", 0))],
    ]
    info_table = Table(info_data, colWidths=[75, 195, 80, 150])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#374151")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("\u2501" * 70, subtitle_style))

    # ── Section 1: Daily Hours & Tips Breakdown ────────────────────────────
    elements.append(Paragraph("DAILY HOURS &amp; TIPS BREAKDOWN", section_style))

    day_data = profile.get("day_data", {})
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]

    daily_header = ["Day", "Shift", "Position", "Hours", "Rate", "Wages", "Tips"]
    daily_rows = [daily_header]

    day_totals_hours = 0.0
    day_totals_wages = 0.0
    day_totals_tips = 0.0

    for day_name in day_order:
        entries = day_data.get(day_name, [])
        if not entries:
            continue
        for entry in entries:
            hrs = entry.get("hours", 0)
            wage_rate = entry.get("hourly_wage", 0)
            wages = entry.get("wages", 0)
            tip_val = entry.get("total_tip", 0) or (
                entry.get("floor_tip", 0) + entry.get("bar_tip", 0))

            daily_rows.append([
                day_name[:3],
                entry.get("shift", ""),
                entry.get("position", ""),
                f"{hrs:.1f}",
                _fmt_r(wage_rate) + "/hr" if wage_rate else "",
                _fmt_r(wages),
                _fmt_r(tip_val),
            ])
            day_totals_hours += hrs
            day_totals_wages += wages
            day_totals_tips += tip_val

    # Totals row
    daily_rows.append(["TOTAL", "", "", f"{day_totals_hours:.1f}", "",
                        _fmt_r(day_totals_wages), _fmt_r(day_totals_tips)])

    dt = Table(daily_rows, colWidths=[40, 55, 110, 45, 65, 75, 75])
    n_rows = len(daily_rows)
    dt.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1B2A4A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#F0F9FF")),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2),
         [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    elements.append(dt)
    elements.append(Spacer(1, 6))

    # ── Section 2: Earnings Summary ────────────────────────────────────────
    elements.append(Paragraph("EARNINGS SUMMARY", section_style))

    reg_wages = pr["regular_wages"]
    ot_wages = pr["overtime_wages"]
    tips_total = pr["total_tips"]
    gross_pay = round(reg_wages + ot_wages + tips_total, 2)

    rate_str = fmt(pr["hourly_rate"]) if pr["hourly_rate"] != "split" else "split"
    earn_data = [
        ["Description", "Details", "Amount"],
        ["Regular Wages", f'{pr["regular_hours"]:.1f} hrs @ {rate_str}', _fmt_r(reg_wages)],
        ["Overtime Wages", f'{pr["overtime_hours"]:.1f} hrs', _fmt_r(ot_wages)],
        ["Total Tips", f'Floor: {_fmt_r(profile.get("total_floor", 0))}  '
                       f'Bar: {_fmt_r(profile.get("total_bar", 0))}', _fmt_r(tips_total)],
        ["", "", ""],
        ["GROSS PAY", "", _fmt_r(gross_pay)],
    ]
    et = Table(earn_data, colWidths=[150, 200, 110])
    et.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1B2A4A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#EEF2FF")),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor("#4F46E5")),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(et)
    elements.append(Spacer(1, 6))

    # ── Section 3: Tax Deductions ──────────────────────────────────────────
    ti = emp.get("tax_info", {})
    tax_on = ti.get("tax_enabled", False)

    if tax_on and taxes.get("tax_enabled"):
        elements.append(Paragraph("TAX DEDUCTIONS (EMPLOYEE)", section_style))

        ded_header = ["Tax Type", "Rate / Info", "Weekly Amount"]
        ded_rows = [ded_header]

        ded_items = [
            ("Federal Income Tax", ti.get("federal_filing_status", "Single"),
             taxes["federal_income_tax"]),
            ("Social Security", "6.20%", taxes["social_security"]),
            ("Medicare", "1.45%", taxes["medicare"]),
            ("NY State Income Tax", ti.get("ny_filing_status", "Single"),
             taxes["ny_state_income_tax"]),
            ("NY SDI", "0.50%", taxes["ny_sdi"]),
            ("NY Paid Family Leave", "0.388%", taxes["ny_paid_family_leave"]),
        ]
        if taxes.get("nyc_local_tax", 0) > 0:
            ded_items.append(("NYC Local Tax", "NYC Resident", taxes["nyc_local_tax"]))
        if taxes.get("yonkers_tax", 0) > 0:
            ded_items.append(("Yonkers Tax", "Yonkers Resident", taxes["yonkers_tax"]))

        for label, info, amount in ded_items:
            ded_rows.append([label, info, f"\u2212{_fmt_r(amount)}"])

        ded_rows.append(["", "", ""])
        ded_rows.append(["TOTAL DEDUCTIONS", "", f"\u2212{_fmt_r(taxes['total_deductions'])}"])

        ddt = Table(ded_rows, colWidths=[180, 150, 130])
        ddt.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1B2A4A")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (2, 1), (2, -1), colors.HexColor("#DC2626")),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#FEF2F2")),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(ddt)
        elements.append(Spacer(1, 10))

        # ── Net Pay highlight ──────────────────────────────────────────────
        net_data = [["NET PAY (Take-Home)", _fmt_r(taxes["net_pay"])]]
        nt = Table(net_data, colWidths=[340, 120])
        nt.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#065F46")),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0FDF4")),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor("#065F46")),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor("#065F46")),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(nt)
        elements.append(Spacer(1, 6))

        # ── Section 4: Employer Costs ──────────────────────────────────────
        elements.append(Paragraph("EMPLOYER COSTS (not deducted from employee)", section_style))

        er_header = ["Cost Type", "Weekly Amount"]
        er_rows = [er_header]
        er_items = [
            ("Employer Social Security (6.2%)", taxes["employer_ss"]),
            ("Employer Medicare (1.45%)", taxes["employer_medicare"]),
            ("FUTA (0.6%)", taxes["employer_futa"]),
        ]
        if taxes.get("employer_mctmt", 0) > 0:
            er_items.append(("NY MCTMT", taxes["employer_mctmt"]))
        er_items.append(("Total Employer Tax", taxes["total_employer_tax"]))
        er_items.append(("TOTAL LABOR COST", taxes["total_labor_cost"]))

        for label, amount in er_items:
            er_rows.append([label, _fmt_r(amount)])

        ert = Table(er_rows, colWidths=[340, 120])
        n_er = len(er_rows)
        ert.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -3), 'Helvetica'),
            ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#374151")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#FEF2F2")),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor("#DC2626")),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(ert)
    else:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(
            "Tax calculation is disabled for this employee. "
            "Only gross pay is shown. Enable taxes in the employee settings "
            "to see a full tax breakdown.", subtitle_style))

    # ── Disclaimer ─────────────────────────────────────────────────────────
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        f"Generated on {date.today().strftime('%B %d, %Y')} \u2014 "
        "* Tax calculations are estimates. Consult a CPA for accuracy.",
        small_note))

    doc.build(elements)

    dest = filedialog.asksaveasfilename(
        title="Save Weekly Details PDF",
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        initialfile=filename,
    )
    if dest:
        import shutil
        shutil.copy2(str(filepath), dest)
        app.toast.show(f"Saved \u2192 {Path(dest).name}")
    else:
        app.toast.show(f"PDF created \u2192 payslips/{filename}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PDF EXPORT — Individual Payslip
# ═══════════════════════════════════════════════════════════════════════════════

def _export_payslip_pdf(app, emp, pr, taxes, mon):
    """Generate a professional PDF pay stub for one employee."""
    end_date = mon + timedelta(days=6)
    folder = app.dm.ensure_wk(mon) / "payslips"
    folder.mkdir(exist_ok=True)

    safe_name = emp["name"].replace(" ", "_")
    filename = f"payslip_{safe_name}_{end_date.isoformat()}.pdf"
    filepath = folder / filename

    doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch)

    styles = getSampleStyleSheet()
    elements = []

    # Header styles
    title_style = ParagraphStyle('PayTitle', parent=styles['Title'],
                                 fontSize=16, spaceAfter=6,
                                 alignment=1, textColor=colors.HexColor("#1B2A4A"))
    subtitle_style = ParagraphStyle('PaySub', parent=styles['Normal'],
                                    fontSize=10, alignment=1,
                                    textColor=colors.HexColor("#6B7280"))
    section_style = ParagraphStyle('Section', parent=styles['Heading3'],
                                   fontSize=11, spaceAfter=4, spaceBefore=12,
                                   textColor=colors.HexColor("#374151"))

    # ── Restaurant Header with logo ──────────────────────────────────────
    logo_el = _pdf_logo_element()
    if logo_el:
        elements.append(logo_el)
        elements.append(Spacer(1, 4))
    _rest_name = getattr(app, '_logged_in_restaurant', 'My Restaurant') or 'My Restaurant'
    elements.append(Paragraph(_rest_name.upper(), title_style))
    elements.append(Paragraph("PAY STATEMENT", subtitle_style))
    elements.append(Spacer(1, 12))

    # ── Employee Info Table ───────────────────────────────────────────────
    dept = pr.get("department", "FOH")
    info_data = [
        ["Employee:", emp["name"], "ID:", emp["id"]],
        ["Position:", f"{pr['positions']} ({dept})", "Pay Period:",
         f"{mon.strftime('%b %d')} \u2013 {end_date.strftime('%b %d, %Y')}"],
        ["", "", "Pay Date:", end_date.strftime("%b %d, %Y")],
    ]
    info_table = Table(info_data, colWidths=[70, 200, 70, 160])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#374151")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 10))

    # ── Earnings ──────────────────────────────────────────────────────────
    elements.append(Paragraph("\u2501" * 60, subtitle_style))
    elements.append(Paragraph("EARNINGS", section_style))

    reg_wages = pr["regular_wages"]
    ot_wages = pr["overtime_wages"]
    tips = pr["total_tips"]
    gross = round(reg_wages + ot_wages + tips, 2)

    rate_str = fmt(pr["hourly_rate"]) if pr["hourly_rate"] != "split" else "split"

    earn_data = [
        ["Regular", f'{pr["regular_hours"]:.1f} hrs @ {rate_str}', "", _fmt_r(reg_wages)],
        ["Overtime", f'{pr["overtime_hours"]:.1f} hrs', "", _fmt_r(ot_wages)],
        ["Tips", "", "", _fmt_r(tips)],
        ["", "", "", ""],
        ["Gross Pay", "", "", _fmt_r(gross)],
    ]
    earn_table = Table(earn_data, colWidths=[100, 180, 60, 100])
    earn_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#1C1C1E")),
        ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(earn_table)

    # ── Deductions (if tax enabled) ───────────────────────────────────────
    if taxes.get("tax_enabled"):
        elements.append(Paragraph("DEDUCTIONS", section_style))

        ded_data = []
        for label, key in [
            ("Federal Income Tax", "federal_income_tax"),
            ("Social Security (6.2%)", "social_security"),
            ("Medicare (1.45%)", "medicare"),
            ("NY State Income Tax", "ny_state_income_tax"),
            ("NY SDI", "ny_sdi"),
            ("NY Paid Family Leave", "ny_paid_family_leave"),
        ]:
            ded_data.append([label, "", "", f"\u2212{_fmt_r(taxes[key])}"])

        if taxes.get("nyc_local_tax", 0) > 0:
            ded_data.append(["NYC Local Tax", "", "", f"\u2212{_fmt_r(taxes['nyc_local_tax'])}"])
        if taxes.get("yonkers_tax", 0) > 0:
            ded_data.append(["Yonkers Tax", "", "", f"\u2212{_fmt_r(taxes['yonkers_tax'])}"])

        ded_data.append(["", "", "", ""])
        ded_data.append(["Total Deductions", "", "", f"\u2212{_fmt_r(taxes['total_deductions'])}"])

        ded_table = Table(ded_data, colWidths=[200, 80, 60, 100])
        ded_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (3, 0), (3, -1), colors.HexColor("#DC2626")),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('LINEABOVE', (0, -1), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(ded_table)
        elements.append(Spacer(1, 8))

        # Net Pay
        net_data = [["NET PAY", "", "", _fmt_r(taxes["net_pay"])]]
        net_table = Table(net_data, colWidths=[200, 80, 60, 100])
        net_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 14),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#065F46")),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor("#1B2A4A")),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor("#1B2A4A")),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(net_table)

    # ── Check Reduction (if enabled) ──────────────────────────────────────
    red_data = emp.get("reduction", {})
    if red_data.get("enabled", False):
        red_pct = red_data.get("percentage", 10)
        if taxes.get("tax_enabled"):
            pay_before_red = taxes["net_pay"]
        else:
            pay_before_red = gross
        red_amount = round(pay_before_red * red_pct / 100, 2)
        pay_after_red = round(pay_before_red - red_amount, 2)

        elements.append(Spacer(1, 8))
        elements.append(Paragraph(f"CHECK REDUCTION ({red_pct}%)", section_style))

        red_data_rows = [
            ["Pay before reduction", "", "", _fmt_r(pay_before_red)],
            [f"Reduction ({red_pct}%)", "", "", f"\u2212{_fmt_r(red_amount)}"],
            ["", "", "", ""],
            ["FINAL PAY (After Reduction)", "", "", _fmt_r(pay_after_red)],
        ]
        red_table = Table(red_data_rows, colWidths=[200, 80, 60, 100])
        red_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 14),
            ('TEXTCOLOR', (3, 1), (3, 1), colors.HexColor("#DC2626")),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor("#92400E")),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('LINEABOVE', (0, -1), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#FEF3C7")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, -1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, -1), (-1, -1), 8),
        ]))
        elements.append(red_table)

    # ── Employer Costs ────────────────────────────────────────────────────
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("EMPLOYER COSTS (not deducted from employee)", section_style))

    er_data = [
        ["Employer SS + Medicare", _fmt_r(taxes["employer_ss"] + taxes["employer_medicare"])],
        ["FUTA", _fmt_r(taxes["employer_futa"])],
    ]
    if taxes.get("employer_mctmt", 0) > 0:
        er_data.append(["NY MCTMT", _fmt_r(taxes["employer_mctmt"])])
    er_data.append(["Total Labor Cost", _fmt_r(taxes["total_labor_cost"])])

    er_table = Table(er_data, colWidths=[300, 140])
    er_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('LINEABOVE', (0, -1), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(er_table)

    # ── Disclaimer ────────────────────────────────────────────────────────
    elements.append(Spacer(1, 20))
    disc_style = ParagraphStyle('Disc', parent=styles['Normal'], fontSize=7,
                                textColor=colors.HexColor("#9CA3AF"),
                                alignment=1)
    elements.append(Paragraph("* Tax calculations are estimates. Consult a CPA.", disc_style))

    doc.build(elements)

    dest = filedialog.asksaveasfilename(
        title="Save Payslip PDF",
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        initialfile=filename,
    )
    if dest:
        import shutil
        shutil.copy2(str(filepath), dest)
        app.toast.show(f"Saved \u2192 {Path(dest).name}")
    else:
        app.toast.show(f"PDF created \u2192 payslips/{filename}")


def _export_payslip_csv(app, emp, pr, taxes, mon):
    """Export a single employee's payslip as CSV."""
    end_date = mon + timedelta(days=6)
    folder = app.dm.ensure_wk(mon) / "payslips"
    folder.mkdir(exist_ok=True)

    safe_name = emp["name"].replace(" ", "_")
    filename = f"payslip_{safe_name}_{end_date.isoformat()}.csv"
    filepath = folder / filename

    rows = [
        {"Category": "Earnings", "Item": "Regular Wages",
         "Amount": round(pr["regular_wages"], 2)},
        {"Category": "Earnings", "Item": "Overtime Wages",
         "Amount": round(pr["overtime_wages"], 2)},
        {"Category": "Earnings", "Item": "Tips",
         "Amount": round(pr["total_tips"], 2)},
        {"Category": "Earnings", "Item": "Gross Pay",
         "Amount": round(pr["regular_wages"] + pr["overtime_wages"] + pr["total_tips"], 2)},
    ]

    if taxes.get("tax_enabled"):
        for label, key in [
            ("Federal Income Tax", "federal_income_tax"),
            ("Social Security", "social_security"),
            ("Medicare", "medicare"),
            ("NY State Income Tax", "ny_state_income_tax"),
            ("NY SDI", "ny_sdi"),
            ("NY Paid Family Leave", "ny_paid_family_leave"),
            ("NYC Local Tax", "nyc_local_tax"),
            ("Yonkers Tax", "yonkers_tax"),
        ]:
            val = taxes.get(key, 0)
            if val > 0 or "Federal" in label or "Social" in label or "Medicare" in label or "NY State" in label:
                rows.append({"Category": "Deduction", "Item": label,
                             "Amount": -round(val, 2)})
        rows.append({"Category": "Deduction", "Item": "Total Deductions",
                     "Amount": -round(taxes["total_deductions"], 2)})
        rows.append({"Category": "Net", "Item": "Net Pay",
                     "Amount": round(taxes["net_pay"], 2)})

    # Check Reduction
    _red_data = emp.get("reduction", {})
    if _red_data.get("enabled", False):
        _red_pct = _red_data.get("percentage", 10)
        _gross = round(pr["regular_wages"] + pr["overtime_wages"] + pr["total_tips"], 2)
        _pbr = taxes["net_pay"] if taxes.get("tax_enabled") else _gross
        _red_amt = round(_pbr * _red_pct / 100, 2)
        _par = round(_pbr - _red_amt, 2)
        rows.append({"Category": "Reduction", "Item": f"Check Reduction ({_red_pct}%)",
                     "Amount": -round(_red_amt, 2)})
        rows.append({"Category": "Reduction", "Item": "Final Pay (After Reduction)",
                     "Amount": _par})

    for label, key in [
        ("Employer SS", "employer_ss"), ("Employer Medicare", "employer_medicare"),
        ("FUTA", "employer_futa"), ("NY MCTMT", "employer_mctmt"),
    ]:
        val = taxes.get(key, 0)
        if val > 0:
            rows.append({"Category": "Employer Cost", "Item": label,
                         "Amount": round(val, 2)})
    rows.append({"Category": "Employer Cost", "Item": "Total Labor Cost",
                 "Amount": round(taxes["total_labor_cost"], 2)})

    _rest_name = getattr(app, '_logged_in_restaurant', 'My Restaurant') or 'My Restaurant'
    with open(filepath, "w", newline="") as f:
        # Branding header row
        f.write(f"Generated by Stamhad Payroll | Restaurant: {_rest_name} | "
                f"Week: {mon.strftime('%b %d')}-{end_date.strftime('%d %Y')}\n")
        w = csv.DictWriter(f, fieldnames=["Category", "Item", "Amount"])
        w.writeheader()
        w.writerows(rows)

    dest = filedialog.asksaveasfilename(
        title="Save Payslip CSV",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        initialfile=filename,
    )
    if dest:
        import shutil
        shutil.copy2(str(filepath), dest)
        app.toast.show(f"Saved \u2192 {Path(dest).name}")
    else:
        app.toast.show(f"CSV created \u2192 payslips/{filename}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PDF EXPORT — Full Payroll (All Employees)
# ═══════════════════════════════════════════════════════════════════════════════

def _export_all_pdf(app, mon):
    """Generate a single PDF with cover page + one page per employee + summary."""
    end_date = mon + timedelta(days=6)
    folder = app.dm.ensure_wk(mon)

    filename = f"full_payroll_{end_date.isoformat()}.pdf"
    filepath = folder / filename

    payroll = app.dm.gen_payroll(mon)
    if not payroll:
        app.toast.show("No payroll data to export.", bg=WARN_BG, fg=WARN_FG)
        return

    doc = SimpleDocTemplate(str(filepath), pagesize=letter,
                            topMargin=0.5 * inch, bottomMargin=0.5 * inch,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = []

    cover_title = ParagraphStyle('CoverTitle', parent=styles['Title'],
                                 fontSize=24, spaceAfter=12, alignment=1,
                                 textColor=colors.HexColor("#1B2A4A"))
    cover_sub = ParagraphStyle('CoverSub', parent=styles['Normal'],
                               fontSize=14, alignment=1,
                               textColor=colors.HexColor("#6B7280"))
    cover_stat = ParagraphStyle('CoverStat', parent=styles['Normal'],
                                fontSize=12, alignment=1, spaceBefore=6,
                                textColor=colors.HexColor("#1C1C1E"))

    # ── Cover Page with logo ─────────────────────────────────────────────
    elements.append(Spacer(1, 60))
    logo_el = _pdf_logo_element()
    if logo_el:
        elements.append(logo_el)
        elements.append(Spacer(1, 12))
    _rest_name = getattr(app, '_logged_in_restaurant', 'My Restaurant') or 'My Restaurant'
    elements.append(Paragraph(_rest_name.upper(), cover_title))
    elements.append(Paragraph("WEEKLY PAYROLL REPORT", cover_sub))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        f"{mon.strftime('%B %d')} \u2013 {end_date.strftime('%B %d, %Y')}", cover_sub))
    elements.append(Spacer(1, 40))

    total_gross = sum(r["regular_wages"] + r["overtime_wages"] + r["total_tips"]
                      for r in payroll)
    total_emp = len(payroll)

    # Compute total net and labor cost
    total_net = 0.0
    total_labor = 0.0
    all_taxes = {}
    for pr in payroll:
        emp_obj = app.dm.emp_by_id(pr["emp_id"])
        ti = emp_obj.get("tax_info", {}) if emp_obj else {}
        gp = round(pr["regular_wages"] + pr["overtime_wages"] + pr["total_tips"], 2)
        ytd = taxcalc.compute_ytd_gross(BASE_DIR, pr["emp_id"], mon)
        tx = taxcalc.compute_weekly_taxes(gp, ti, ytd_gross=ytd)
        all_taxes[pr["emp_id"]] = tx
        total_net += tx["net_pay"]
        total_labor += tx["total_labor_cost"]

    elements.append(Paragraph(f"Total Employees: {total_emp}", cover_stat))
    elements.append(Paragraph(f"Total Gross Pay: {_fmt_r(total_gross)}", cover_stat))
    elements.append(Paragraph(f"Total Net Pay: {_fmt_r(total_net)}", cover_stat))
    elements.append(Paragraph(f"Total Labor Cost: {_fmt_r(total_labor)}", cover_stat))

    elements.append(PageBreak())

    # ── One page per employee ─────────────────────────────────────────────
    section_style = ParagraphStyle('SectHead', parent=styles['Heading3'],
                                   fontSize=11, spaceAfter=4, spaceBefore=8,
                                   textColor=colors.HexColor("#374151"))
    normal = ParagraphStyle('Norm', parent=styles['Normal'], fontSize=9)

    for pr in payroll:
        emp_obj = app.dm.emp_by_id(pr["emp_id"])
        if not emp_obj:
            continue
        tx = all_taxes[pr["emp_id"]]
        gp = round(pr["regular_wages"] + pr["overtime_wages"] + pr["total_tips"], 2)
        dept = pr.get("department", "FOH")

        elements.append(Paragraph(f"{_rest_name.upper()} \u2014 PAY STATEMENT",
                                  ParagraphStyle('ps', parent=styles['Title'],
                                                 fontSize=13, alignment=1,
                                                 textColor=colors.HexColor("#1B2A4A"))))
        elements.append(Spacer(1, 8))

        info_data = [
            ["Employee:", emp_obj["name"], "ID:", emp_obj["id"]],
            ["Position:", f"{pr['positions']} ({dept})", "Period:",
             f"{mon.strftime('%b %d')} \u2013 {end_date.strftime('%b %d, %Y')}"],
        ]
        info_t = Table(info_data, colWidths=[65, 200, 50, 170])
        info_t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(info_t)

        # Earnings
        elements.append(Paragraph("EARNINGS", section_style))
        rate_s = fmt(pr["hourly_rate"]) if pr["hourly_rate"] != "split" else "split"
        earn_d = [
            ["Regular", f'{pr["regular_hours"]:.1f} hrs @ {rate_s}', _fmt_r(pr["regular_wages"])],
            ["Overtime", f'{pr["overtime_hours"]:.1f} hrs', _fmt_r(pr["overtime_wages"])],
            ["Tips", "", _fmt_r(pr["total_tips"])],
            ["Gross Pay", "", _fmt_r(gp)],
        ]
        et = Table(earn_d, colWidths=[120, 200, 120])
        et.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('LINEABOVE', (0, -1), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(et)

        if tx.get("tax_enabled"):
            elements.append(Paragraph("DEDUCTIONS", section_style))
            dd = []
            for lbl, k in [("Federal", "federal_income_tax"),
                            ("SS (6.2%)", "social_security"),
                            ("Medicare (1.45%)", "medicare"),
                            ("NY State", "ny_state_income_tax"),
                            ("NY SDI", "ny_sdi"),
                            ("NY PFL", "ny_paid_family_leave")]:
                dd.append([lbl, f"\u2212{_fmt_r(tx[k])}"])
            if tx.get("nyc_local_tax", 0) > 0:
                dd.append(["NYC Tax", f"\u2212{_fmt_r(tx['nyc_local_tax'])}"])
            if tx.get("yonkers_tax", 0) > 0:
                dd.append(["Yonkers", f"\u2212{_fmt_r(tx['yonkers_tax'])}"])
            dd.append(["Total Deductions", f"\u2212{_fmt_r(tx['total_deductions'])}"])
            dd.append(["NET PAY", _fmt_r(tx["net_pay"])])

            dt = Table(dd, colWidths=[320, 120])
            dt.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, -2), (-1, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (1, 0), (1, -3), colors.HexColor("#DC2626")),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor("#065F46")),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('LINEABOVE', (0, -2), (-1, -2), 0.5, colors.HexColor("#D1D5DB")),
                ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor("#1B2A4A")),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(dt)

        # Check Reduction (if enabled)
        _red_data = emp_obj.get("reduction", {})
        if _red_data.get("enabled", False):
            _red_pct = _red_data.get("percentage", 10)
            _pbr = tx["net_pay"] if tx.get("tax_enabled") else gp
            _red_amt = round(_pbr * _red_pct / 100, 2)
            _par = round(_pbr - _red_amt, 2)
            elements.append(Paragraph(f"CHECK REDUCTION ({_red_pct}%)", section_style))
            _rd = [
                ["Pay before reduction", _fmt_r(_pbr)],
                [f"Reduction ({_red_pct}%)", f"\u2212{_fmt_r(_red_amt)}"],
                ["FINAL PAY", _fmt_r(_par)],
            ]
            _rt = Table(_rd, colWidths=[320, 120])
            _rt.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor("#DC2626")),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.HexColor("#92400E")),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#FEF3C7")),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('LINEABOVE', (0, -1), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(_rt)

        # Employer
        elements.append(Spacer(1, 6))
        er_d = [
            ["Employer SS+Med", _fmt_r(tx["employer_ss"] + tx["employer_medicare"])],
            ["FUTA", _fmt_r(tx["employer_futa"])],
            ["Total Labor Cost", _fmt_r(tx["total_labor_cost"])],
        ]
        ert = Table(er_d, colWidths=[320, 120])
        ert.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#6B7280")),
            ('LINEABOVE', (0, -1), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(ert)
        elements.append(PageBreak())

    # ── Summary Page ──────────────────────────────────────────────────────
    elements.append(Paragraph("PAYROLL SUMMARY", cover_title))
    elements.append(Spacer(1, 12))

    sum_header = ["Employee", "Dept", "Gross", "Deductions", "Net Pay", "ER Tax", "Labor Cost"]
    sum_rows = [sum_header]
    for pr in payroll:
        tx = all_taxes[pr["emp_id"]]
        gp = round(pr["regular_wages"] + pr["overtime_wages"] + pr["total_tips"], 2)
        sum_rows.append([
            pr["employee_name"], pr["department"],
            _fmt_r(gp), _fmt_r(tx["total_deductions"]),
            _fmt_r(tx["net_pay"]), _fmt_r(tx["total_employer_tax"]),
            _fmt_r(tx["total_labor_cost"]),
        ])

    sum_rows.append([
        "TOTAL", "",
        _fmt_r(total_gross), _fmt_r(sum(all_taxes[pr["emp_id"]]["total_deductions"] for pr in payroll)),
        _fmt_r(total_net),
        _fmt_r(sum(all_taxes[pr["emp_id"]]["total_employer_tax"] for pr in payroll)),
        _fmt_r(total_labor),
    ])

    st = Table(sum_rows, colWidths=[120, 35, 70, 70, 70, 60, 75])
    st.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1B2A4A")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#F0F9FF")),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#F9FAFB")]),
    ]))
    elements.append(st)

    doc.build(elements)

    dest = filedialog.asksaveasfilename(
        title="Save Full Payroll PDF",
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        initialfile=filename,
    )
    if dest:
        import shutil
        shutil.copy2(str(filepath), dest)
        app.toast.show(f"Saved \u2192 {Path(dest).name}")
    else:
        app.toast.show(f"PDF created \u2192 {filename}")


def _fmt_r(val):
    """Format as $X,XXX.XX string."""
    try:
        return f"${float(val):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


# ═══════════════════════════════════════════════════════════════════════════════
#  INTEGRATION — Patch the main App class
# ═══════════════════════════════════════════════════════════════════════════════

def _switch_classic(app):
    app._payroll_v2_active = False
    app._clr()
    app.pg_payroll()


_v2_installed = False  # prevent double-patching

def install_payroll_v2(app_class):
    """
    Monkey-patch the App class to add Payroll V2 nav item,
    replace the employee edit modal, and add user/logout display.
    Safe to call multiple times — only patches once.
    """
    global _v2_installed
    if _v2_installed:
        return
    _v2_installed = True

    original_build_nav = app_class._build_nav
    original_emp_dlg = app_class._emp_dlg

    def patched_build_nav(self):
        original_build_nav(self)
        nav = list(self.nav_btns.values())[0].master

        # Add Payroll V2 to nav (guard against duplicates)
        if "Payroll V2" not in self.nav_btns:
            b = tk.Label(nav, text="Detailed Payroll", bg=BG_NAV, fg="#94A3B8",
                         font=(FONT, 11, "bold"), padx=14, pady=6, cursor="hand2")
            b.pack(side="left", padx=2, pady=8)
            b.bind("<Button-1>", lambda e: self.nav_click("Payroll V2"))
            b.bind("<Enter>", lambda e, w=b: w.config(bg="#2D4A7A") if w.cget("bg") != "#4F46E5" else None)
            b.bind("<Leave>", lambda e, w=b: w.config(bg=BG_NAV) if w.cget("bg") != "#4F46E5" else None)
            self.nav_btns["Payroll V2"] = b

    original_nav_click = app_class.nav_click

    def patched_nav_click(self, lbl):
        for n, b in self.nav_btns.items():
            b.config(bg="#4F46E5" if n == lbl else BG_NAV,
                     fg="#FFFFFF" if n == lbl else "#94A3B8")
        self._screen = lbl
        for w in self.main.winfo_children():
            w.destroy()

        if lbl == "Payroll V2":
            pg_payroll_v2(self)
        else:
            self._payroll_v2_active = False
            screen_map = {
                "Today": self.pg_today, "Week View": self.pg_week,
                "Employees": self.pg_emps, "Positions": self.pg_pos,
                "Payroll Report": self.pg_payroll,
            }
            fn = screen_map.get(lbl)
            if fn:
                fn()

    def patched_emp_dlg(self, emp=None):
        _emp_dlg_v2(self, emp)

    def patched_do_logout(self):
        """Sign out: clear saved session and restart as login screen."""
        import auth_manager as auth_mod
        auth_mod.clear_session()
        self.destroy()
        import login_screen
        login_screen.require_login(_launch_app)

    # ── Override Toast CSV import to fix Time In / Time Out display ────────
    def patched_import_toast_csv(self):
        path = filedialog.askopenfilename(
            title="Select Toast CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                all_rows = list(reader)
        except Exception as ex:
            messagebox.showerror("Import Error", f"Could not read CSV:\n{ex}")
            return
        if len(all_rows) < 2:
            messagebox.showinfo("Import", "CSV file is empty.")
            return

        header = [h.strip().lower() for h in all_rows[0]]
        print("[V2] CSV HEADER:", header)

        def _col(name):
            try:
                return header.index(name)
            except ValueError:
                return -1

        i_emp = _col("employee")
        i_job = _col("job")
        i_ti  = _col("time in")
        i_to  = _col("time out")
        i_hrs = _col("payable hours")
        if i_hrs < 0:
            i_hrs = _col("total hours")
        print(f"[V2] COLUMNS: emp={i_emp} job={i_job} ti={i_ti} to={i_to} hrs={i_hrs}")

        parsed = []
        for row in all_rows[1:]:
            emp  = row[i_emp].strip()  if 0 <= i_emp < len(row) else ""
            job  = row[i_job].strip()  if 0 <= i_job < len(row) else ""
            ti   = row[i_ti].strip()   if 0 <= i_ti  < len(row) else ""
            to_v = row[i_to].strip()   if 0 <= i_to  < len(row) else ""
            hrs  = row[i_hrs].strip()  if 0 <= i_hrs < len(row) else "0"
            print(f"[V2]   {emp!r}  job={job!r}  ti={ti!r}  to={to_v!r}  hrs={hrs!r}")
            parsed.append([emp, job, ti, to_v, hrs])
        if not parsed:
            messagebox.showinfo("Import", "No data rows.")
            return
        self._show_time_entry_preview_v2(parsed)

    def patched_show_preview(self, parsed_rows):
        if not parsed_rows:
            messagebox.showinfo("No Data", "Empty.")
            return

        win = tk.Toplevel(self)
        win.title(f"Toast Time Entries — {self.sel_date.strftime('%A, %b %d')}")
        win.geometry("980x620")
        win.resizable(True, True)
        win.transient(self)
        win.grab_set()

        top_hdr = tk.Frame(win, bg=BG_NAV)
        top_hdr.pack(fill="x")
        tk.Label(top_hdr, text=f"  Time Entries Preview — {self.sel_date.strftime('%A, %b %d, %Y')}",
                 bg=BG_NAV, fg="#FFFFFF", font=(FONT, 14, "bold")).pack(side="left", padx=12, pady=10)
        tk.Label(top_hdr, text=f"{len(parsed_rows)} entries",
                 bg=BG_NAV, fg="#94A3B8", font=(FONT, 11)).pack(side="left", padx=8)

        table_frame = tk.Frame(win, bg=BG_PAGE)
        table_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(table_frame, bg=BG_PAGE, highlightthickness=0)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG_PAGE)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _mw(event):
            if platform.system() == "Darwin":
                d = event.delta
                if abs(d) < 5:
                    d = d * 3
                canvas.yview_scroll(int(-d), "units")
            else:
                canvas.yview_scroll(int(-event.delta / 120), "units")
        canvas.bind_all("<MouseWheel>", _mw)

        cols = ["#", "Employee", "Job", "Time In", "Time Out", "Hours", "Skip"]
        widths = [3, 20, 14, 10, 10, 7, 5]
        hdr = tk.Frame(inner, bg=ACCENT)
        hdr.pack(fill="x", padx=8, pady=(8, 0))
        for c, w in zip(cols, widths):
            tk.Label(hdr, text=c, bg=ACCENT, fg="#FFFFFF", font=(FONT, 11, "bold"),
                     width=w, anchor="w", padx=6).pack(side="left", pady=6)

        row_widgets = []
        for idx, row in enumerate(parsed_rows):
            bg = ROW_A if idx % 2 == 0 else ROW_B
            rf = tk.Frame(inner, bg=bg)
            rf.pack(fill="x", padx=8)

            emp, job, ti_val, to_val, hrs_val = row[0], row[1], row[2], row[3], row[4]
            print(f"[V2] DISPLAY ROW {idx}: ti={ti_val!r} to={to_val!r} hrs={hrs_val!r}")

            tk.Label(rf, text=str(idx+1), bg=bg, fg=FG_SEC, font=(FONT,10), width=3, anchor="w", padx=6).pack(side="left", pady=4)
            tk.Label(rf, text=emp, bg=bg, fg=FG, font=(FONT,11), width=20, anchor="w", padx=6).pack(side="left", pady=4)
            tk.Label(rf, text=job, bg=bg, fg=FG_SEC, font=(FONT,11), width=14, anchor="w", padx=6).pack(side="left", pady=4)

            ti_e = tk.Entry(rf, width=10, font=(FONT,11), relief="solid", bd=1)
            ti_e.pack(side="left", padx=4, pady=4)
            if ti_val:
                ti_e.insert(tk.END, ti_val)

            to_e = tk.Entry(rf, width=10, font=(FONT,11), relief="solid", bd=1)
            to_e.pack(side="left", padx=4, pady=4)
            if to_val:
                to_e.insert(tk.END, to_val)

            hrs_e = tk.Entry(rf, width=7, font=(FONT,11), relief="solid", bd=1)
            hrs_e.pack(side="left", padx=4, pady=4)
            if hrs_val:
                hrs_e.insert(tk.END, hrs_val)

            skip_v = tk.BooleanVar(master=win, value=False)
            tk.Checkbutton(rf, variable=skip_v, bg=bg, activebackground=bg).pack(side="left", padx=8)

            def _recalc(event, ti=ti_e, to=to_e, he=hrs_e):
                try:
                    t1 = datetime.strptime(ti.get().strip(), "%I:%M %p")
                    t2 = datetime.strptime(to.get().strip(), "%I:%M %p")
                    diff = (t2 - t1).seconds if t2 > t1 else (t2 - t1).seconds + 86400
                    he.delete(0, tk.END); he.insert(0, str(round(diff/3600, 2)))
                except Exception:
                    pass
            ti_e.bind("<FocusOut>", _recalc)
            to_e.bind("<FocusOut>", _recalc)

            row_widgets.append({"emp": emp, "job": job, "ti_e": ti_e, "to_e": to_e, "hrs_e": hrs_e, "skip": skip_v})

        # Store refs on window so nothing gets GC'd
        win._rw = row_widgets

        btn_bar = tk.Frame(win, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        btn_bar.pack(fill="x", side="bottom")
        tk.Label(btn_bar, text=f"{len(parsed_rows)} entries  |  Edit times, then click Import",
                 bg=BG_CARD, fg=FG_SEC, font=(FONT,11)).pack(side="left", padx=16, pady=10)

        def _do_import():
            edited = []
            for rw in row_widgets:
                if rw["skip"].get():
                    continue
                edited.append({
                    "Employee": rw["emp"], "Job": rw["job"],
                    "Time In": rw["ti_e"].get().strip(),
                    "Time Out": rw["to_e"].get().strip(),
                    "Payable Hours": rw["hrs_e"].get().strip(),
                })
            canvas.unbind_all("<MouseWheel>")
            win.destroy()
            self._import_toast_rows(edited)

        def _cancel():
            canvas.unbind_all("<MouseWheel>")
            win.destroy()

        Btn(btn_bar, text="Cancel", style="cancel", command=_cancel).pack(side="right", padx=8, pady=8)
        Btn(btn_bar, text="\u2713  Import Selected", style="primary", command=_do_import).pack(side="right", padx=8, pady=8)

    # ── Override Toast SFTP download — SFTP uses different column names ─────
    def patched_download_toast_sftp(self):
        from payroll_app import (PARAMIKO_OK, SFTP_HOST, SFTP_PORT,
            SFTP_USERNAME, SFTP_EXPORT_ID, SFTP_DEFAULT_KEY, _payroll_data_dir,
            BASE_DIR)
        import threading

        if not PARAMIKO_OK:
            from payroll_app import _PARAMIKO_ERR
            messagebox.showerror("Missing Package",
                f"The 'paramiko' package is required.\n\npip install paramiko\n\nError: {_PARAMIKO_ERR}")
            return

        # Find SSH key — try Firebase first, then local, then ask user
        key_path = None
        import os, shutil

        # 1) Try to load from Firebase (per-restaurant)
        fb_key = self.dm.load_toast_ssh_key()
        if fb_key and fb_key.exists():
            key_path = fb_key
            print("[V2] SSH key loaded from Firebase")

        # 2) Try local candidates
        if not key_path:
            candidates = [
                SFTP_DEFAULT_KEY,
                _payroll_data_dir() / "toast_rsa_key",
                BASE_DIR / "keys" / "toast_rsa_key",
                Path.home() / "Library" / "Application Support" / "AnemiRoomCharge" / "keys" / "toast_rsa_key",
                Path(os.environ.get("APPDATA", str(Path.home()))) / "AnemiRoomCharge" / "keys" / "toast_rsa_key",
            ]
            for c in candidates:
                if c.exists():
                    key_path = c
                    break

        # 3) Ask user to select key file
        if not key_path:
            key_path = filedialog.askopenfilename(
                title="Select Toast SSH Key (toast_rsa_key)",
                filetypes=[("All files", "*")])
            if not key_path:
                return
            key_path = Path(key_path)
            dest = SFTP_DEFAULT_KEY
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(key_path), str(dest))
            key_path = dest

        # Auto-upload to Firebase if found locally but not in Firebase
        if key_path and not fb_key:
            if self.dm.save_toast_ssh_key(key_path):
                print("[V2] SSH key auto-uploaded to Firebase")

        date_str = self.sel_date.strftime("%Y%m%d")
        date_display = self.sel_date.strftime("%A, %b %d")

        prog = tk.Toplevel(self)
        prog.title("Downloading from Toast")
        prog.geometry("360x120")
        prog.resizable(False, False)
        prog.transient(self)
        prog.grab_set()
        tk.Label(prog, text=f"Downloading TimeEntries for {date_display}...",
                 font=(FONT, 12)).pack(pady=20)
        prog_lbl = tk.Label(prog, text="Connecting to SFTP...", fg=FG_SEC, font=(FONT, 11))
        prog_lbl.pack()
        prog.update()

        import paramiko as _paramiko

        def _worker():
            try:
                pkey = _paramiko.RSAKey.from_private_key_file(str(key_path))
                client = _paramiko.SSHClient()
                client.set_missing_host_key_policy(_paramiko.AutoAddPolicy())
                client.connect(hostname=SFTP_HOST, port=SFTP_PORT,
                               username=SFTP_USERNAME, pkey=pkey,
                               look_for_keys=False, allow_agent=False, timeout=30)
                sftp = client.open_sftp()
                remote_path = f"/{SFTP_EXPORT_ID}/{date_str}/TimeEntries.csv"
                try:
                    sftp.stat(remote_path)
                except FileNotFoundError:
                    sftp.close(); client.close()
                    self.after(0, lambda: _on_error(
                        f"TimeEntries.csv not found for {date_display}.\nPath: {remote_path}"))
                    return
                with sftp.open(remote_path, "r") as f:
                    csv_data = f.read().decode("utf-8-sig")
                sftp.close(); client.close()
                self.after(0, lambda d=csv_data: _on_success(d))
            except Exception as ex:
                self.after(0, lambda: _on_error(str(ex)))

        def _on_error(msg):
            try:
                prog.destroy()
            except Exception:
                pass
            messagebox.showerror("SFTP Error", f"Download failed:\n{msg}")

        def _on_success(csv_data):
            try:
                prog.destroy()
            except Exception:
                pass
            all_rows = list(csv.reader(io.StringIO(csv_data)))
            if len(all_rows) < 2:
                messagebox.showinfo("No Data", f"TimeEntries for {date_display} is empty.")
                return
            header = [h.strip().lower() for h in all_rows[0]]
            def _col(*names):
                for n in names:
                    try:
                        return header.index(n)
                    except ValueError:
                        continue
                return -1
            # Support both SFTP format (In Date/Out Date/Job Title)
            # and manual export format (Time In/Time Out/Job)
            i_emp = _col("employee")
            i_job = _col("job title", "job")
            i_ti  = _col("in date", "time in")
            i_to  = _col("out date", "time out")
            i_hrs = _col("payable hours", "total hours")
            parsed = []
            for row in all_rows[1:]:
                emp  = row[i_emp].strip()  if 0 <= i_emp < len(row) else ""
                job  = row[i_job].strip()  if 0 <= i_job < len(row) else ""
                ti   = row[i_ti].strip()   if 0 <= i_ti  < len(row) else ""
                to_v = row[i_to].strip()   if 0 <= i_to  < len(row) else ""
                hrs  = row[i_hrs].strip()  if 0 <= i_hrs < len(row) else "0"
                # "In Date"/"Out Date" may be full datetime — extract time
                if ti and " " in ti:
                    parts = ti.split(" ", 1)
                    if "/" in parts[0] or "-" in parts[0]:
                        ti = parts[1]
                if to_v and " " in to_v:
                    parts = to_v.split(" ", 1)
                    if "/" in parts[0] or "-" in parts[0]:
                        to_v = parts[1]
                parsed.append([emp, job, ti, to_v, hrs])
            self._show_time_entry_preview_v2(parsed)

        threading.Thread(target=_worker, daemon=True).start()

    def patched_upload_ssh_key(self):
        """Let user select an SSH key file and upload it to Firebase."""
        path = filedialog.askopenfilename(
            title="Select Toast SSH Key (toast_rsa_key)",
            filetypes=[("All files", "*")],
        )
        if not path:
            return
        ok = self.dm.save_toast_ssh_key(path)
        if ok:
            messagebox.showinfo("SSH Key", "Toast SSH key uploaded to Firebase successfully.\n\nAll users of this restaurant can now download from Toast.")
        else:
            messagebox.showerror("SSH Key", "Failed to upload SSH key to Firebase.\nCheck your internet connection.")

    # ── Feature: Unsaved changes popup ───────────────────────────────────
    # Track clean state when Today page loads, warn on navigation if dirty

    original_pg_today = app_class.pg_today

    def patched_pg_today(self):
        """Wrap pg_today to snapshot clean state after loading."""
        original_pg_today(self)
        # Snapshot the clean state right after loading
        self._snapshot_hours_from_widgets()
        self._snapshot_checked_from_widgets()
        self._snapshot_tips_from_widgets()
        self._clean_hours = list(self._hours_data)
        self._clean_checked = set(self._checked_emp_ids)
        self._clean_tips = dict(self._day_tips)
        self._clean_tip_values = dict(getattr(self, '_tip_entry_values', {}))

    def _has_unsaved_changes(self):
        """Check if current Today page data differs from the clean snapshot."""
        if not hasattr(self, '_clean_hours'):
            return False
        if self._screen != "Today":
            return False
        # Snapshot current widget state
        self._snapshot_hours_from_widgets()
        self._snapshot_checked_from_widgets()
        self._snapshot_tips_from_widgets()
        # Compare checked employees
        if self._checked_emp_ids != self._clean_checked:
            return True
        # Compare hours data
        if len(self._hours_data) != len(self._clean_hours):
            return True
        for cur, orig in zip(self._hours_data, self._clean_hours):
            if (cur.get("emp_id") != orig.get("emp_id") or
                cur.get("hours") != orig.get("hours") or
                cur.get("position_name") != orig.get("position_name") or
                cur.get("shift") != orig.get("shift") or
                cur.get("points") != orig.get("points")):
                return True
        # Compare tip entry values
        cur_tips = getattr(self, '_tip_entry_values', {})
        if cur_tips != self._clean_tip_values:
            return True
        return False

    def _confirm_discard(self):
        """Show save/discard/cancel dialog. Returns True if user wants to proceed."""
        result = messagebox.askyesnocancel(
            "Unsaved Changes",
            "You have unsaved changes. Do you want to save before leaving?",
            icon="warning"
        )
        if result is True:
            # Save
            self._save_day()
            return True
        elif result is False:
            # Discard
            return True
        else:
            # Cancel — stay on page
            return False

    original_prev_day = app_class._prev_day
    original_next_day = app_class._next_day

    def patched_prev_day(self):
        if _has_unsaved_changes(self):
            if not _confirm_discard(self):
                return
        original_prev_day(self)

    def patched_next_day(self):
        if _has_unsaved_changes(self):
            if not _confirm_discard(self):
                return
        original_next_day(self)

    def patched_nav_click_with_save(self, lbl):
        if _has_unsaved_changes(self):
            if not _confirm_discard(self):
                return
        # Clear clean state so we don't re-trigger
        self._clean_hours = []
        self._clean_checked = set()
        self._clean_tips = {}
        self._clean_tip_values = {}
        patched_nav_click(self, lbl)

    def _on_close(self):
        if _has_unsaved_changes(self):
            if not _confirm_discard(self):
                return
        self.destroy()

    # ── Feature: Auto-add standard wage employees with 0 hours ─────────

    original_build_tab_employees = app_class._build_tab_employees

    def patched_build_tab_employees(self):
        """After building the employee tab, auto-check fixed-wage employees."""
        original_build_tab_employees(self)
        # Auto-check fixed-wage employees that aren't already checked
        for emp in self.dm.employees:
            eid = emp["id"]
            if eid in self._checked_emp_ids:
                continue
            # Check if any of their positions has a fixed weekly wage
            has_fixed = False
            for pa in emp.get("positions", []):
                pos_name = pa.get("position_name", "") if isinstance(pa, dict) else pa
                pos = self.dm.pos_by_name(pos_name)
                if pos:
                    fwv = pos.get("fixed_weekly_wage")
                    if fwv and safe_float(fwv) > 0:
                        has_fixed = True
                        break
            if has_fixed:
                # Check the checkbox if it exists
                if hasattr(self, '_check_vars') and eid in self._check_vars:
                    self._check_vars[eid].set(True)
                    self._checked_emp_ids.add(eid)

    app_class._import_toast_csv = patched_import_toast_csv
    app_class._download_toast_sftp = patched_download_toast_sftp
    app_class._show_time_entry_preview_v2 = patched_show_preview
    app_class._upload_toast_ssh_key = patched_upload_ssh_key

    app_class._build_nav = patched_build_nav
    app_class.nav_click = patched_nav_click_with_save
    app_class._emp_dlg = patched_emp_dlg
    app_class._do_logout = patched_do_logout
    app_class.pg_today = patched_pg_today
    app_class._prev_day = patched_prev_day
    app_class._next_day = patched_next_day
    app_class._build_tab_employees = patched_build_tab_employees
    app_class._has_unsaved_changes = _has_unsaved_changes
    app_class._confirm_discard = _confirm_discard
    app_class._on_close = _on_close
    app_class._payroll_v2_active = False
    app_class._logged_in_user = ""
    app_class._logged_in_display = ""
    app_class._logged_in_role = ""
    app_class._logged_in_uid = ""
    app_class._logged_in_restaurant = "My Restaurant"


# ═══════════════════════════════════════════════════════════════════════════════
#  APP LAUNCHER (called after successful login)
# ═══════════════════════════════════════════════════════════════════════════════

def _launch_app(email, display_name, role, uid="", restaurant_name=""):
    """Create and run the main app after successful authentication."""
    restaurant_name = restaurant_name or "My Restaurant"

    # If admin, open admin panel instead of payroll app
    if role == "admin":
        import admin_panel
        panel = admin_panel.AdminPanel()
        panel.mainloop()
        return

    from payroll_app import seed
    seed()
    install_payroll_v2(App)

    # Set user info BEFORE creating App so _build_nav can use it
    App._logged_in_user = email
    App._logged_in_display = display_name
    App._logged_in_role = role
    App._logged_in_uid = uid
    App._logged_in_restaurant = restaurant_name

    app = App()

    # ── Unsaved changes: intercept window close ───────────────────────────
    app.protocol("WM_DELETE_WINDOW", lambda: app._on_close())

    # ── Update window title with restaurant name ─────────────────────────
    app.title(f"Stamhad Payroll \u2014 {restaurant_name}")

    # ── Rebrand nav bar ──────────────────────────────────────────────────
    try:
        nav = list(app.nav_btns.values())[0].master

        # Remove the date nav frame (far right) to make room for user menu
        # The brand label ("Stamhad Payroll") is already set in payroll_app.py

        # Restaurant name in center
        rest_lbl = tk.Label(nav, text=f"\u2022 {restaurant_name}",
                             bg=BG_NAV, fg="#A5B4FC",
                             font=(FONT, 10, "bold"))
        rest_lbl.pack(side="right", padx=(0, 4), pady=8)

        # User menu frame (right side)
        user_frame = tk.Frame(nav, bg=BG_NAV)
        user_frame.pack(side="right", padx=(0, 8), pady=8)

        # User dropdown trigger
        menu_lbl = tk.Label(user_frame, text="\u2630", bg=BG_NAV,
                             fg="#B0C4DE", font=(FONT, 14), cursor="hand2")
        menu_lbl.pack(side="left")

        # Create dropdown menu
        dropdown = tk.Menu(app, tearoff=0, font=(FONT, 10),
                            bg=BG_CARD, fg=FG,
                            activebackground=ACCENT, activeforeground="#FFFFFF")
        dropdown.add_command(
            label=f"  {restaurant_name}",
            state="disabled")
        dropdown.add_separator()
        dropdown.add_command(
            label="  Toast SSH Key",
            command=lambda: _toast_ssh_key_settings(app))
        dropdown.add_command(
            label="  Check for Updates",
            command=lambda: _check_updates_manual(app))
        dropdown.add_separator()
        dropdown.add_command(
            label="  Sign Out",
            command=lambda: app._do_logout())

        def _show_menu(e):
            try:
                dropdown.tk_popup(e.x_root, e.y_root + 10)
            except Exception:
                pass

        menu_lbl.bind("<Button-1>", _show_menu)

    except Exception:
        pass

    app.mainloop()


def _toast_ssh_key_settings(app):
    """Show a dialog to manage the Toast SFTP SSH key."""
    from payroll_app import _payroll_data_dir, SFTP_DEFAULT_KEY

    win = tk.Toplevel(app)
    win.title("Toast SSH Key")
    win.geometry("480x280")
    win.resizable(False, False)
    win.transient(app)
    win.grab_set()

    tk.Label(win, text="Toast SFTP SSH Key", font=(FONT, 14, "bold"),
             bg=BG_PAGE, fg=FG).pack(pady=(16, 4))
    tk.Label(win, text="This key is used to download time entries from Toast.",
             font=(FONT, 11), bg=BG_PAGE, fg=FG_SEC).pack(pady=(0, 12))

    # Status
    status_var = tk.StringVar(value="Checking...")
    status_lbl = tk.Label(win, textvariable=status_var, font=(FONT, 11),
                          bg=BG_PAGE, fg=FG)
    status_lbl.pack(pady=4)

    def _check_status():
        # Check Firebase
        fb_key = app.dm.load_toast_ssh_key()
        if fb_key and fb_key.exists():
            status_var.set("\u2705  SSH key is stored in Firebase (synced)")
            status_lbl.config(fg=SUCCESS)
        elif SFTP_DEFAULT_KEY.exists():
            status_var.set("\u26A0\uFE0F  SSH key found locally only (not synced)")
            status_lbl.config(fg="#D97706")
        else:
            status_var.set("\u274C  No SSH key configured")
            status_lbl.config(fg=DANGER)

    def _upload_key():
        path = filedialog.askopenfilename(
            parent=win,
            title="Select Toast SSH Key (toast_rsa_key)",
            filetypes=[("All files", "*")])
        if not path:
            return
        # Validate it looks like an SSH private key
        try:
            with open(path, "r", errors="ignore") as f:
                first_line = f.readline().strip()
            if "PRIVATE KEY" not in first_line and "BEGIN" not in first_line:
                if not messagebox.askyesno("Warning",
                        "This file doesn't look like an SSH private key.\n"
                        "SSH keys usually start with '-----BEGIN RSA PRIVATE KEY-----'.\n\n"
                        f"Selected: {Path(path).name}\n\nUpload anyway?",
                        parent=win):
                    return
        except Exception:
            pass
        # Save locally
        import shutil
        SFTP_DEFAULT_KEY.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, str(SFTP_DEFAULT_KEY))
        # Upload to Firebase
        ok = app.dm.save_toast_ssh_key(path)
        if ok:
            messagebox.showinfo("SSH Key",
                "Key saved and uploaded to Firebase.\n\n"
                "All computers using this restaurant account can now download from Toast.",
                parent=win)
        else:
            messagebox.showwarning("SSH Key",
                "Key saved locally but could not upload to Firebase.\n"
                "Check your internet connection.",
                parent=win)
        _check_status()

    def _sync_to_firebase():
        if SFTP_DEFAULT_KEY.exists():
            ok = app.dm.save_toast_ssh_key(SFTP_DEFAULT_KEY)
            if ok:
                messagebox.showinfo("SSH Key", "Key uploaded to Firebase.", parent=win)
            else:
                messagebox.showerror("SSH Key", "Upload failed.", parent=win)
            _check_status()
        else:
            messagebox.showwarning("SSH Key", "No local key to upload.", parent=win)

    btn_frame = tk.Frame(win, bg=BG_PAGE)
    btn_frame.pack(pady=16)

    Btn(btn_frame, text="\U0001F4C2  Browse & Upload Key",
        style="primary", command=_upload_key).pack(pady=4, padx=20, fill="x")
    Btn(btn_frame, text="\u2601  Sync Local Key to Firebase",
        style="ghost", command=_sync_to_firebase).pack(pady=4, padx=20, fill="x")
    Btn(btn_frame, text="Close", style="cancel",
        command=win.destroy).pack(pady=(8, 0), padx=20, fill="x")

    _check_status()


def _check_updates_manual(app):
    """Manual update check triggered from menu."""
    try:
        from updater import Updater
        from updater.update_dialog import show_update_dialog
        updater = Updater(
            github_username="pipilas",
            github_repo="anemi-payroll",
            app_name="Stamhad Payroll",
        )
        import threading

        def _worker():
            try:
                result = updater.check_for_updates()
                if result.get("update_available"):
                    app.after(0, lambda: show_update_dialog(app, updater, result))
                else:
                    app.after(0, lambda: _show_no_update(app, result))
            except Exception as e:
                app.after(0, lambda: _show_update_error(app, str(e)))

        threading.Thread(target=_worker, daemon=True).start()
    except Exception:
        pass


def _show_no_update(app, result):
    """Show 'up to date' message."""
    from tkinter import messagebox
    messagebox.showinfo(
        "Stamhad Payroll",
        f"You're up to date!\nVersion {result.get('current_version', '?')}",
        parent=app)


def _show_update_error(app, msg):
    """Show update check error."""
    from tkinter import messagebox
    messagebox.showwarning(
        "Update Check Failed",
        f"Could not check for updates.\n{msg[:100]}",
        parent=app)


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # ── Silent auto-update BEFORE anything else ──────────────────────────
    # If an update is found, it downloads, installs, relaunches, and exits.
    # If no update (or no internet), it continues to the login screen.
    try:
        from updater import Updater
        _updater = Updater(
            github_username="pipilas",
            github_repo="anemi-payroll",
            app_name="Stamhad Payroll",
        )
        _updater.silent_auto_update()
    except Exception:
        pass  # Any failure — just launch the app normally

    import login_screen
    login_screen.require_login(_launch_app)
