"""
Stamhad Payroll — Admin Panel
Create restaurant accounts via Firebase Authentication.
Metadata stored in Realtime Database. Enable/disable accounts.
"""

import tkinter as tk
from tkinter import messagebox
import threading
import string
import secrets
import auth_manager as auth

# ── Colours ─────────────────────────────────────────────────────────────────
BG_PAGE  = "#F1F5F9"
BG_CARD  = "#FFFFFF"
BG_NAV   = "#1B2A4A"
BG_INPUT = "#F9FAFB"
ACCENT   = "#4F46E5"
ACCENT_HV = "#4338CA"
FG       = "#1C1C1E"
FG_SEC   = "#6B7280"
DANGER   = "#DC2626"
SUCCESS  = "#059669"
SUCCESS_BG = "#ECFDF5"
BORDER   = "#D1D5DB"
FONT     = "Helvetica Neue"

PLANS = ["Trial", "Standard", "Premium", "Enterprise"]


def _generate_temp_password(length=10):
    """Generate a random temporary password."""
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


# ═══════════════════════════════════════════════════════════════════════════════
#  ADD NEW RESTAURANT MODAL
# ═══════════════════════════════════════════════════════════════════════════════

class AddRestaurantDialog(tk.Toplevel):
    """Modal: create a new restaurant account via Firebase Auth + DB."""

    def __init__(self, parent, on_created=None):
        super().__init__(parent)
        self.title("Add New Restaurant")
        self.configure(bg=BG_CARD)
        self.geometry("540x700")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._on_created = on_created
        self._build_ui()

    def _build_ui(self):
        tk.Label(self, text="Add New Restaurant", bg=BG_CARD, fg=ACCENT,
                 font=(FONT, 18, "bold")).pack(pady=(20, 4))
        tk.Label(self, text="Creates a Firebase Auth account + DB record",
                 bg=BG_CARD, fg=FG_SEC, font=(FONT, 11)).pack(pady=(0, 12))
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=30)

        form = tk.Frame(self, bg=BG_CARD)
        form.pack(fill="both", expand=True, padx=30, pady=(12, 0))

        self.fields = {}

        specs = [
            ("restaurant_name", "Restaurant Name", "e.g. My Restaurant"),
            ("owner_name",      "Owner Name",      "e.g. John Smith"),
            ("email",           "Email",            "e.g. owner@restaurant.com"),
            ("password",        "Password",         ""),
            ("app_name",        "App Name",         "e.g. Stamhad Payroll"),
            ("notes",           "Notes (optional)",  ""),
        ]

        for key, label, placeholder in specs:
            tk.Label(form, text=label, bg=BG_CARD, fg=FG,
                     font=(FONT, 11, "bold")).pack(anchor="w", pady=(8, 0))

            if key == "password":
                pw_frame = tk.Frame(form, bg=BG_CARD)
                pw_frame.pack(fill="x", pady=(2, 0))
                entry = tk.Entry(pw_frame, font=(FONT, 12),
                                  highlightthickness=1, highlightcolor=ACCENT,
                                  highlightbackground=BORDER, relief="flat",
                                  bg=BG_INPUT)
                entry.pack(side="left", fill="x", expand=True)
                gen_btn = tk.Label(pw_frame, text=" Generate ", bg=ACCENT,
                                    fg="#FFFFFF", font=(FONT, 10, "bold"),
                                    padx=8, pady=4, cursor="hand2")
                gen_btn.pack(side="right", padx=(6, 0))
                gen_btn.bind("<Button-1>",
                              lambda e, ent=entry: self._gen_pw(ent))
                gen_btn.bind("<Enter>",
                              lambda e, w=gen_btn: w.config(bg=ACCENT_HV))
                gen_btn.bind("<Leave>",
                              lambda e, w=gen_btn: w.config(bg=ACCENT))
                entry.insert(0, _generate_temp_password())
            else:
                entry = tk.Entry(form, font=(FONT, 12),
                                  highlightthickness=1, highlightcolor=ACCENT,
                                  highlightbackground=BORDER, relief="flat",
                                  bg=BG_INPUT)
                entry.pack(fill="x", pady=(2, 0))
                if placeholder:
                    entry.config(fg="#9CA3AF")
                    entry.insert(0, placeholder)
                    entry.bind("<FocusIn>",
                               lambda e, ent=entry, ph=placeholder:
                               self._clear_ph(ent, ph))
                    entry.bind("<FocusOut>",
                               lambda e, ent=entry, ph=placeholder:
                               self._set_ph(ent, ph))

            self.fields[key] = entry

        # Plan
        tk.Label(form, text="Plan", bg=BG_CARD, fg=FG,
                 font=(FONT, 11, "bold")).pack(anchor="w", pady=(8, 0))
        self.plan_var = tk.StringVar(value="Standard")
        pf = tk.Frame(form, bg=BG_CARD)
        pf.pack(fill="x", pady=(2, 0))
        for p in PLANS:
            tk.Radiobutton(pf, text=p, variable=self.plan_var, value=p,
                            bg=BG_CARD, fg=FG, selectcolor=BG_INPUT,
                            activebackground=BG_CARD,
                            font=(FONT, 10)).pack(side="left", padx=(0, 12))

        # Enabled toggle
        self.enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(form, text="Account Enabled",
                        variable=self.enabled_var, bg=BG_CARD, fg=FG,
                        selectcolor=BG_INPUT, activebackground=BG_CARD,
                        font=(FONT, 11)).pack(anchor="w", pady=(10, 0))

        self.err_lbl = tk.Label(self, text="", bg=BG_CARD, fg=DANGER,
                                 font=(FONT, 10, "bold"), wraplength=460)
        self.err_lbl.pack(pady=(8, 0))

        btn_row = tk.Frame(self, bg=BG_CARD)
        btn_row.pack(pady=(6, 16))

        cancel_lbl = tk.Label(btn_row, text="  Cancel  ", bg=BORDER, fg=FG,
                               font=(FONT, 12, "bold"), padx=16, pady=8,
                               cursor="hand2")
        cancel_lbl.pack(side="left", padx=(0, 12))
        cancel_lbl.bind("<Button-1>", lambda e: self.destroy())

        cr_btn = tk.Frame(btn_row, bg=SUCCESS, cursor="hand2")
        cr_btn.pack(side="left")
        cr_lbl = tk.Label(cr_btn, text="  Create Account  ", bg=SUCCESS,
                           fg="#FFFFFF", font=(FONT, 12, "bold"),
                           padx=16, pady=8, cursor="hand2")
        cr_lbl.pack()
        for w in (cr_btn, cr_lbl):
            w.bind("<Button-1>", lambda e: self._create())
            w.bind("<Enter>", lambda e: cr_btn.config(bg="#047857") or cr_lbl.config(bg="#047857"))
            w.bind("<Leave>", lambda e: cr_btn.config(bg=SUCCESS) or cr_lbl.config(bg=SUCCESS))

    def _clear_ph(self, entry, ph):
        if entry.get() == ph:
            entry.delete(0, "end")
            entry.config(fg=FG)

    def _set_ph(self, entry, ph):
        if not entry.get().strip():
            entry.insert(0, ph)
            entry.config(fg="#9CA3AF")

    def _gen_pw(self, entry):
        entry.delete(0, "end")
        entry.insert(0, _generate_temp_password())

    def _get(self, key, ph=""):
        val = self.fields[key].get().strip()
        return "" if val == ph else val

    def _create(self):
        restaurant_name = self._get("restaurant_name", "e.g. My Restaurant")
        owner_name = self._get("owner_name", "e.g. John Smith")
        email = self._get("email", "e.g. owner@restaurant.com")
        password = self._get("password")
        app_name = self._get("app_name", "e.g. Stamhad Payroll")
        notes = self._get("notes")
        plan = self.plan_var.get()
        enabled = self.enabled_var.get()

        if not restaurant_name:
            self.err_lbl.config(text="Restaurant name is required.")
            return
        if not owner_name:
            self.err_lbl.config(text="Owner name is required.")
            return
        if not email or "@" not in email:
            self.err_lbl.config(text="Enter a valid email address.")
            return
        if not password or len(password) < 6:
            self.err_lbl.config(
                text="Password must be at least 6 characters (Firebase requirement).")
            return

        self.err_lbl.config(text="Creating account in Firebase...", fg=FG_SEC)
        self.update()

        def _thread():
            try:
                auth.create_restaurant_account(
                    email=email, password=password,
                    restaurant_name=restaurant_name,
                    owner_name=owner_name,
                    app_name=app_name or "Stamhad Payroll",
                    plan=plan, notes=notes,
                    enabled=enabled, role="restaurant",
                )
                self.after(0, lambda: self._ok(
                    email, password, restaurant_name, owner_name, plan))
            except Exception as ex:
                self.after(0, lambda: self.err_lbl.config(
                    text=f"Error: {ex}", fg=DANGER))

        threading.Thread(target=_thread, daemon=True).start()

    def _ok(self, email, password, restaurant_name, owner_name, plan):
        self.destroy()
        if self._on_created:
            self._on_created(email, password, restaurant_name,
                             owner_name, plan)


# ═══════════════════════════════════════════════════════════════════════════════
#  CREDENTIAL CARD
# ═══════════════════════════════════════════════════════════════════════════════

class CredentialCard(tk.Toplevel):
    """Shows newly created credentials with copy button."""

    def __init__(self, parent, email, password, restaurant_name,
                 owner_name, plan):
        super().__init__(parent)
        self.title("Account Created")
        self.configure(bg=BG_CARD)
        self.geometry("480x420")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="\u2705", bg=BG_CARD,
                 font=(FONT, 36)).pack(pady=(20, 0))
        tk.Label(self, text="Account Created Successfully!", bg=BG_CARD,
                 fg=SUCCESS, font=(FONT, 16, "bold")).pack(pady=(4, 12))
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=30)

        info = tk.Frame(self, bg=SUCCESS_BG, highlightbackground=SUCCESS,
                         highlightthickness=1)
        info.pack(fill="x", padx=30, pady=(16, 8))

        rows = [
            ("Restaurant", restaurant_name),
            ("Owner", owner_name),
            ("Plan", plan),
            ("Email", email),
            ("Password", password),
        ]
        for lbl, val in rows:
            r = tk.Frame(info, bg=SUCCESS_BG)
            r.pack(fill="x", padx=16, pady=(6, 0))
            tk.Label(r, text=f"{lbl}:", bg=SUCCESS_BG, fg=FG_SEC,
                     font=(FONT, 10, "bold"), width=14,
                     anchor="w").pack(side="left")
            tk.Label(r, text=val, bg=SUCCESS_BG, fg=FG,
                     font=(FONT, 11)).pack(side="left")
        tk.Frame(info, bg=SUCCESS_BG, height=8).pack()

        copy_text = (
            f"Restaurant: {restaurant_name}\n"
            f"Owner: {owner_name}\n"
            f"Plan: {plan}\n"
            f"Email: {email}\n"
            f"Password: {password}\n"
        )

        self._copy_lbl = None

        def _copy(e=None):
            self.clipboard_clear()
            self.clipboard_append(copy_text)
            if self._copy_lbl:
                self._copy_lbl.config(text="\u2705 Copied!")
                self.after(2000, lambda: (
                    self._copy_lbl.config(text="  Copy Credentials  ")
                    if self._copy_lbl.winfo_exists() else None))

        cb = tk.Frame(self, bg=ACCENT, cursor="hand2")
        cb.pack(pady=(12, 0))
        self._copy_lbl = tk.Label(cb, text="  Copy Credentials  ",
                                   bg=ACCENT, fg="#FFFFFF",
                                   font=(FONT, 12, "bold"),
                                   padx=16, pady=8, cursor="hand2")
        self._copy_lbl.pack()
        for w in (cb, self._copy_lbl):
            w.bind("<Button-1>", _copy)
            w.bind("<Enter>", lambda e: cb.config(bg=ACCENT_HV) or self._copy_lbl.config(bg=ACCENT_HV))
            w.bind("<Leave>", lambda e: cb.config(bg=ACCENT) or self._copy_lbl.config(bg=ACCENT))

        cl = tk.Label(self, text="Close", bg=BG_CARD, fg=FG_SEC,
                       font=(FONT, 11), cursor="hand2")
        cl.pack(pady=(8, 16))
        cl.bind("<Button-1>", lambda e: self.destroy())


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN PANEL — Main Window
# ═══════════════════════════════════════════════════════════════════════════════

class AdminPanel(tk.Tk):
    """Admin panel for managing restaurant accounts."""

    def __init__(self):
        super().__init__()
        self.title("Stamhad Payroll \u2014 Admin Panel")
        self.configure(bg=BG_PAGE)
        self.geometry("920x620")
        self.minsize(800, 500)
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        top = tk.Frame(self, bg=BG_NAV, height=56)
        top.pack(fill="x")
        top.pack_propagate(False)

        tk.Label(top, text="Stamhad Payroll", bg=BG_NAV, fg="#FFFFFF",
                 font=(FONT, 18, "bold")).pack(side="left", padx=16)
        tk.Label(top, text="Admin Panel", bg=BG_NAV, fg="#94A3B8",
                 font=(FONT, 13)).pack(side="left", padx=(4, 0))

        add_btn = tk.Frame(top, bg=SUCCESS, cursor="hand2")
        add_btn.pack(side="right", padx=16, pady=12)
        add_lbl = tk.Label(add_btn, text="  + Add New Restaurant  ",
                            bg=SUCCESS, fg="#FFFFFF",
                            font=(FONT, 11, "bold"), padx=8, pady=4,
                            cursor="hand2")
        add_lbl.pack()
        for w in (add_btn, add_lbl):
            w.bind("<Button-1>", lambda e: self._add_restaurant())
            w.bind("<Enter>", lambda e: add_btn.config(bg="#047857") or add_lbl.config(bg="#047857"))
            w.bind("<Leave>", lambda e: add_btn.config(bg=SUCCESS) or add_lbl.config(bg=SUCCESS))

        ref_lbl = tk.Label(top, text="Refresh", bg=BG_NAV, fg="#7EB8FF",
                            font=(FONT, 11), cursor="hand2")
        ref_lbl.pack(side="right", padx=(0, 12))
        ref_lbl.bind("<Button-1>", lambda e: self._refresh_list())

        self.content = tk.Frame(self, bg=BG_PAGE)
        self.content.pack(fill="both", expand=True, padx=16, pady=16)

        self.status_lbl = tk.Label(self, text="", bg=BG_PAGE, fg=FG_SEC,
                                    font=(FONT, 10))
        self.status_lbl.pack(side="bottom", pady=(0, 8))

    def _add_restaurant(self):
        def on_created(email, password, rname, oname, plan):
            CredentialCard(self, email, password, rname, oname, plan)
            self._refresh_list()
        AddRestaurantDialog(self, on_created)

    def _refresh_list(self):
        for w in self.content.winfo_children():
            w.destroy()
        self.status_lbl.config(text="Loading...")
        self.update()

        def _load():
            try:
                data = auth.list_restaurants()
                self.after(0, lambda: self._render(data))
            except Exception as ex:
                self.after(0, lambda: self._render_err(str(ex)))

        threading.Thread(target=_load, daemon=True).start()

    def _render_err(self, msg):
        self.status_lbl.config(text="")
        tk.Label(self.content, text=f"Error: {msg}", bg=BG_PAGE, fg=DANGER,
                 font=(FONT, 12)).pack(pady=20)

    def _render(self, restaurants):
        self.status_lbl.config(text=f"{len(restaurants)} account(s)")

        if not restaurants:
            tk.Label(self.content, text="No restaurant accounts yet.",
                     bg=BG_PAGE, fg=FG_SEC, font=(FONT, 14)).pack(pady=40)
            return

        # Header
        hdr = tk.Frame(self.content, bg=BG_NAV)
        hdr.pack(fill="x")
        for text, w in [("Email", 200), ("Restaurant", 160), ("Owner", 140),
                         ("Plan", 80), ("Status", 80), ("Actions", 100)]:
            tk.Label(hdr, text=text, bg=BG_NAV, fg="#FFFFFF",
                     font=(FONT, 10, "bold"), width=w // 8,
                     anchor="w").pack(side="left", padx=6, pady=6)

        # Scrollable list
        canvas = tk.Canvas(self.content, bg=BG_PAGE, highlightthickness=0)
        sb = tk.Scrollbar(self.content, orient="vertical",
                           command=canvas.yview)
        sf = tk.Frame(canvas, bg=BG_PAGE)
        sf.bind("<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=sf, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        i = 0
        for uid, data in sorted(restaurants.items(),
                                  key=lambda x: x[1].get("email", "")):
            if data.get("role") == "admin":
                continue

            bg = "#FFFFFF" if i % 2 == 0 else "#F8FAFC"
            row = tk.Frame(sf, bg=bg)
            row.pack(fill="x")

            enabled = data.get("enabled", False)
            st_text = "Active" if enabled else "Suspended"
            st_fg = SUCCESS if enabled else DANGER

            for text, w in [
                (data.get("email", uid), 200),
                (data.get("restaurant_name", ""), 160),
                (data.get("owner_name", ""), 140),
                (data.get("plan", "Standard"), 80),
            ]:
                tk.Label(row, text=text, bg=bg, fg=FG, font=(FONT, 10),
                         width=w // 8, anchor="w").pack(
                    side="left", padx=6, pady=6)

            tk.Label(row, text=st_text, bg=bg, fg=st_fg,
                     font=(FONT, 10, "bold"), width=10,
                     anchor="w").pack(side="left", padx=6, pady=6)

            af = tk.Frame(row, bg=bg)
            af.pack(side="left", padx=6, pady=4)

            if enabled:
                dl = tk.Label(af, text="Disable", bg=DANGER, fg="#FFFFFF",
                               font=(FONT, 9, "bold"), padx=6, pady=2,
                               cursor="hand2")
                dl.pack(side="left")
                dl.bind("<Button-1>",
                         lambda e, u=uid: self._toggle(u, False))
            else:
                el = tk.Label(af, text="Enable", bg=SUCCESS, fg="#FFFFFF",
                               font=(FONT, 9, "bold"), padx=6, pady=2,
                               cursor="hand2")
                el.pack(side="left")
                el.bind("<Button-1>",
                         lambda e, u=uid: self._toggle(u, True))

            i += 1

    def _toggle(self, uid, enable):
        action = "enable" if enable else "disable"
        if not messagebox.askyesno(
                f"Confirm {action.title()}",
                f"Are you sure you want to {action} this account?"):
            return

        def _do():
            try:
                auth.set_account_enabled(uid, enable)
                self.after(0, self._refresh_list)
            except Exception as ex:
                self.after(0, lambda: messagebox.showerror(
                    "Error", f"Failed: {ex}"))

        threading.Thread(target=_do, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    AdminPanel().mainloop()
