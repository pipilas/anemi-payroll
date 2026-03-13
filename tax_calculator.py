"""
Anemi Restaurant — Tax Calculator Module
All tax computation logic for federal, NY State, NYC, Yonkers, FICA, and employer taxes.
Reads brackets/rates from Firebase (shared across all restaurants).
Falls back to local tax_tables_2025.json if Firebase is unreachable.
"""

import json
from pathlib import Path

_TAX_TABLES_PATH = Path(__file__).parent / "tax_tables_2025.json"
_tables = None


def _load_tables():
    global _tables
    if _tables is None:
        # Try Firebase first (shared global tax tables)
        try:
            from firebase_db import load_tax_tables_from_firebase
            remote = load_tax_tables_from_firebase()
            if remote:
                _tables = remote
                # Cache locally so offline works
                try:
                    with open(_TAX_TABLES_PATH, "w") as f:
                        json.dump(remote, f, indent=2)
                except Exception:
                    pass
                return _tables
        except Exception:
            pass

        # Fall back to local file
        with open(_TAX_TABLES_PATH) as f:
            _tables = json.load(f)
    return _tables


def _bracket_tax(annual_income, brackets):
    """Compute progressive tax through a bracket list."""
    tax = 0.0
    for b in brackets:
        lo, hi, rate = b["min"], b["max"], b["rate"]
        if annual_income <= lo:
            break
        taxable = min(annual_income, hi) - lo
        tax += taxable * rate
    return tax


def safe_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN TAX COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════════

def compute_weekly_taxes(gross_weekly, emp_tax_info, ytd_gross=0.0):
    """
    Compute all tax withholdings for one week.

    Args:
        gross_weekly: Total gross pay for the week (wages + tips)
        emp_tax_info: Dict of employee tax fields from employees.json
        ytd_gross: Year-to-date gross pay BEFORE this week (for SS cap)

    Returns:
        dict with all tax line items, totals, employer costs
    """
    t = _load_tables()

    if not emp_tax_info or not emp_tax_info.get("tax_enabled"):
        return _no_tax_result(gross_weekly)

    annual_gross = gross_weekly * 52

    # ── Federal Income Tax ────────────────────────────────────────────────
    fed_filing = emp_tax_info.get("federal_filing_status", "Single")
    fed_key = t["filing_status_map"].get(fed_filing, {}).get("federal", "single")

    fed_exempt = emp_tax_info.get("exempt_federal", False)
    if fed_exempt:
        federal_annual = 0.0
    else:
        w4_version = emp_tax_info.get("w4_version", "2020+ New W-4")

        std_deduction = t["federal"]["standard_deduction"].get(fed_key, 15000)
        dependents = safe_float(emp_tax_info.get("dependents_amount", 0))
        other_income = safe_float(emp_tax_info.get("other_income", 0))
        deductions = safe_float(emp_tax_info.get("deductions", 0))
        extra_withholding = safe_float(emp_tax_info.get("extra_withholding", 0))
        multiple_jobs = emp_tax_info.get("multiple_jobs", False)

        adjusted_annual = annual_gross + other_income - deductions
        if not multiple_jobs:
            adjusted_annual -= std_deduction
        else:
            adjusted_annual -= std_deduction / 2

        adjusted_annual = max(adjusted_annual, 0)

        brackets = t["federal"]["brackets"].get(fed_key, t["federal"]["brackets"]["single"])
        federal_annual = _bracket_tax(adjusted_annual, brackets)

        federal_annual -= dependents
        federal_annual = max(federal_annual, 0)
        federal_annual += extra_withholding * 52

    federal_weekly = round(federal_annual / 52, 2)

    # ── FICA — Social Security ────────────────────────────────────────────
    ss_rate = t["fica"]["social_security_rate"]
    ss_wage_base = t["fica"]["social_security_wage_base"]

    if ytd_gross >= ss_wage_base:
        ss_weekly = 0.0
    elif ytd_gross + gross_weekly > ss_wage_base:
        ss_weekly = round((ss_wage_base - ytd_gross) * ss_rate, 2)
    else:
        ss_weekly = round(gross_weekly * ss_rate, 2)

    # ── FICA — Medicare ───────────────────────────────────────────────────
    med_rate = t["fica"]["medicare_rate"]
    medicare_weekly = round(gross_weekly * med_rate, 2)

    add_med_threshold = t["fica"]["additional_medicare_threshold"].get(fed_key, 200000)
    add_med_rate = t["fica"]["additional_medicare_rate"]
    if ytd_gross + gross_weekly > add_med_threshold:
        excess = max(0, ytd_gross + gross_weekly - max(ytd_gross, add_med_threshold))
        medicare_weekly += round(excess * add_med_rate, 2)

    # ── New York State Income Tax ─────────────────────────────────────────
    ny_exempt = emp_tax_info.get("exempt_ny_state", False)
    ny_filing = emp_tax_info.get("ny_filing_status", "Single")
    ny_key = t["ny_filing_status_map"].get(ny_filing, "single")
    ny_extra = safe_float(emp_tax_info.get("ny_additional_withholding", 0))

    if ny_exempt:
        ny_state_weekly = 0.0
    else:
        ny_std = t["new_york_state"]["standard_deduction"].get(ny_key, 8000)
        ny_taxable_annual = max(annual_gross - ny_std, 0)
        ny_brackets = t["new_york_state"]["brackets"].get(ny_key,
                        t["new_york_state"]["brackets"]["single"])
        ny_state_annual = _bracket_tax(ny_taxable_annual, ny_brackets)
        ny_state_annual += ny_extra * 52
        ny_state_weekly = round(ny_state_annual / 52, 2)

    # ── NY SDI ────────────────────────────────────────────────────────────
    sdi_rate = t["new_york_state"]["sdi_rate"]
    sdi_max = t["new_york_state"]["sdi_max_weekly"]
    ny_sdi_weekly = round(min(gross_weekly * sdi_rate, sdi_max), 2)

    # ── NY Paid Family Leave ──────────────────────────────────────────────
    pfl_rate = t["new_york_state"]["paid_family_leave_rate"]
    pfl_base = t["new_york_state"]["paid_family_leave_wage_base"]
    pfl_weekly = round(min(gross_weekly, pfl_base) * pfl_rate, 2)

    # ── NYC Local Tax ─────────────────────────────────────────────────────
    lives_nyc = emp_tax_info.get("lives_in_nyc", False)
    if lives_nyc and not ny_exempt:
        nyc_brackets = t["nyc"]["brackets"]
        nyc_taxable_annual = max(annual_gross - 8000, 0)
        nyc_annual = _bracket_tax(nyc_taxable_annual, nyc_brackets)
        nyc_weekly = round(nyc_annual / 52, 2)
    else:
        nyc_weekly = 0.0

    # ── Yonkers Surcharge ─────────────────────────────────────────────────
    lives_yonkers = emp_tax_info.get("lives_in_yonkers", False)
    if lives_yonkers and not ny_exempt:
        yonkers_rate = t["yonkers"]["surcharge_rate"]
        yonkers_weekly = round(ny_state_weekly * yonkers_rate, 2)
    else:
        yonkers_weekly = 0.0

    # ── Total employee deductions ─────────────────────────────────────────
    total_deductions = round(
        federal_weekly + ss_weekly + medicare_weekly +
        ny_state_weekly + ny_sdi_weekly + pfl_weekly +
        nyc_weekly + yonkers_weekly, 2)

    net_pay = round(gross_weekly - total_deductions, 2)

    # ── Employer costs ────────────────────────────────────────────────────
    er = t["employer_taxes"]
    er_ss_rate = er["social_security_rate"]
    er_med_rate = er["medicare_rate"]

    if ytd_gross >= ss_wage_base:
        er_ss = 0.0
    elif ytd_gross + gross_weekly > ss_wage_base:
        er_ss = round((ss_wage_base - ytd_gross) * er_ss_rate, 2)
    else:
        er_ss = round(gross_weekly * er_ss_rate, 2)

    er_medicare = round(gross_weekly * er_med_rate, 2)

    futa_base = er["futa_wage_base"]
    futa_rate = er["futa_rate"]
    if ytd_gross >= futa_base:
        er_futa = 0.0
    elif ytd_gross + gross_weekly > futa_base:
        er_futa = round((futa_base - ytd_gross) * futa_rate, 2)
    else:
        er_futa = round(gross_weekly * futa_rate, 2)

    er_mctmt = round(gross_weekly * er["ny_mctmt_rate"], 2) if er["ny_mctmt_applies"] else 0.0

    total_employer = round(er_ss + er_medicare + er_futa + er_mctmt, 2)
    total_labor_cost = round(gross_weekly + total_employer, 2)

    return {
        "gross_weekly": gross_weekly,
        "tax_enabled": True,

        "federal_income_tax": federal_weekly,
        "social_security": ss_weekly,
        "medicare": medicare_weekly,
        "ny_state_income_tax": ny_state_weekly,
        "ny_sdi": ny_sdi_weekly,
        "ny_paid_family_leave": pfl_weekly,
        "nyc_local_tax": nyc_weekly,
        "yonkers_tax": yonkers_weekly,

        "total_deductions": total_deductions,
        "net_pay": net_pay,

        "employer_ss": er_ss,
        "employer_medicare": er_medicare,
        "employer_futa": er_futa,
        "employer_mctmt": er_mctmt,
        "total_employer_tax": total_employer,
        "total_labor_cost": total_labor_cost,
    }


def _no_tax_result(gross_weekly):
    """Return result dict for employee with tax disabled."""
    t = _load_tables()
    er = t["employer_taxes"]
    ss_wage_base = t["fica"]["social_security_wage_base"]

    er_ss = round(gross_weekly * er["social_security_rate"], 2)
    er_med = round(gross_weekly * er["medicare_rate"], 2)
    er_futa = round(gross_weekly * er["futa_rate"], 2)
    er_mctmt = round(gross_weekly * er["ny_mctmt_rate"], 2) if er["ny_mctmt_applies"] else 0.0
    total_employer = round(er_ss + er_med + er_futa + er_mctmt, 2)

    return {
        "gross_weekly": gross_weekly,
        "tax_enabled": False,

        "federal_income_tax": 0, "social_security": 0, "medicare": 0,
        "ny_state_income_tax": 0, "ny_sdi": 0, "ny_paid_family_leave": 0,
        "nyc_local_tax": 0, "yonkers_tax": 0,
        "total_deductions": 0, "net_pay": gross_weekly,

        "employer_ss": er_ss, "employer_medicare": er_med,
        "employer_futa": er_futa, "employer_mctmt": er_mctmt,
        "total_employer_tax": total_employer,
        "total_labor_cost": round(gross_weekly + total_employer, 2),
    }


def compute_employer_costs_only(gross_weekly, ytd_gross=0.0):
    """Employer taxes for employees with tax_enabled=False (always calculated)."""
    return _no_tax_result(gross_weekly)


def estimate_weekly_from_fields(tax_info, annual_salary_est=30000):
    """Quick estimate for the live preview in the Tax Info tab."""
    weekly_est = annual_salary_est / 52
    return compute_weekly_taxes(weekly_est, tax_info, ytd_gross=0.0)


# ═══════════════════════════════════════════════════════════════════════════════
#  YTD COMPUTATION
# ═══════════════════════════════════════════════════════════════════════════════

def compute_ytd_gross(base_dir, emp_id, up_to_monday):
    """Sum gross pay for an employee from all week folders in the current year."""
    from datetime import date, timedelta
    import csv

    year_start = date(up_to_monday.year, 1, 1)
    # Find first Monday of the year
    mon = year_start
    if mon.weekday() != 0:
        mon = mon - timedelta(days=mon.weekday())

    total = 0.0
    while mon < up_to_monday:
        wk_dir = base_dir / f"week_{mon.isoformat()}"
        for csv_name in ("foh_hours.csv", "boh_hours.csv"):
            csv_path = wk_dir / csv_name
            if csv_path.exists():
                with open(csv_path, newline="") as f:
                    for row in csv.DictReader(f):
                        if row.get("emp_id") == emp_id:
                            total += safe_float(row.get("hours", 0))
        # Also count tips
        tips_path = wk_dir / "weekly_tips.csv"
        if tips_path.exists():
            with open(tips_path, newline="") as f:
                for row in csv.DictReader(f):
                    if row.get("emp_id") == emp_id:
                        total += safe_float(row.get("total_tip", 0))
        mon += timedelta(days=7)

    return total
