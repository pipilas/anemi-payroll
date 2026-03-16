"""
Stamhad Payroll — Login Screen
Uses Firebase Authentication (email + password).
Auto-login: if "Remember me" was checked, saved credentials are used to
re-authenticate with Firebase on every launch.
No self-signup. Admin creates all accounts.
"""

import tkinter as tk
from tkinter import messagebox
import threading, platform
from pathlib import Path
import auth_manager as auth

# ── Icon paths ────────────────────────────────────────────────────────────
_BASE_DIR  = Path(__file__).parent
_ICONS_DIR = _BASE_DIR / "icons" / "png"
_ICO_FILE  = _BASE_DIR / "icons" / "stamhad_payroll_icon_dark.ico"

def _load_icon(name, master=None):
    """Load a PNG from the icons/png folder. Returns PhotoImage or None."""
    try:
        p = _ICONS_DIR / name
        if p.exists():
            return tk.PhotoImage(master=master, file=str(p))
    except Exception:
        pass
    return None

def _set_window_icon(win):
    """Set window icon: .ico on Windows, .png iconphoto elsewhere."""
    if platform.system() == "Windows" and _ICO_FILE.exists():
        try:
            win.iconbitmap(str(_ICO_FILE))
            return
        except Exception:
            pass
    try:
        icon = _load_icon("icon_dark_128.png", master=win)
        if icon:
            win.iconphoto(True, icon)
            win._icon_ref = icon
    except Exception:
        pass

# ── Colours ────────────────────────────────────────────────────────────────
BG_PAGE  = "#F1F5F9"
BG_CARD  = "#FFFFFF"
BG_NAV   = "#1B2A4A"
ACCENT   = "#4F46E5"
ACCENT_HV = "#4338CA"
FG       = "#1C1C1E"
FG_SEC   = "#6B7280"
DANGER   = "#DC2626"
SUCCESS  = "#059669"
BORDER   = "#D1D5DB"
FONT     = "Helvetica Neue"

SUPPORT_EMAIL = "stamhadsoftware@gmail.com"
APP_NAME = "Stamhad Payroll"


# ═══════════════════════════════════════════════════════════════════════════════
#  LOGIN WINDOW — Email + Password (Firebase Auth)
# ═══════════════════════════════════════════════════════════════════════════════

class LoginWindow(tk.Tk):
    """
    Standalone login window using Firebase Authentication.
    Calls on_success(email, display_name, role, uid, restaurant_name) on login.
    """

    def __init__(self, on_success, prefill_email=""):
        super().__init__()
        self.title(APP_NAME)
        self.configure(bg=BG_PAGE)
        self.geometry("440x580")
        self.resizable(False, False)
        self._on_success = on_success
        self._prefill_email = prefill_email

        _set_window_icon(self)
        self._build_ui()

        # Pre-fill email if we have one
        if self._prefill_email:
            self.email_entry.insert(0, self._prefill_email)
            self.remember_var.set(True)
            self.pw_entry.focus_set()

    def _build_ui(self):
        card = tk.Frame(self, bg=BG_CARD, highlightbackground=BORDER,
                         highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor="center", width=380, height=500)

        # ── Branding header: icon + text ─────────────────────────────────
        self._login_icon = _load_icon("icon_dark_64.png", master=self)
        if self._login_icon:
            tk.Label(card, image=self._login_icon, bg=BG_CARD).pack(pady=(24, 6))
        tk.Label(card, text=APP_NAME, bg=BG_CARD, fg=BG_NAV,
                 font=(FONT, 24, "bold")).pack(pady=(0, 0))
        tk.Label(card, text="by Stamhad Software", bg=BG_CARD, fg=FG_SEC,
                 font=(FONT, 10)).pack(pady=(2, 6))
        tk.Frame(card, bg=ACCENT, height=3, width=60).pack(pady=(0, 18))

        # Email
        tk.Label(card, text="Email", bg=BG_CARD, fg=FG,
                 font=(FONT, 11, "bold"), anchor="w").pack(fill="x", padx=40)
        self.email_entry = tk.Entry(card, font=(FONT, 13), width=24,
                                     highlightthickness=2, highlightcolor=ACCENT,
                                     highlightbackground=BORDER, relief="flat",
                                     bg="#F9FAFB")
        self.email_entry.pack(fill="x", padx=40, pady=(4, 14))

        # Password
        tk.Label(card, text="Password", bg=BG_CARD, fg=FG,
                 font=(FONT, 11, "bold"), anchor="w").pack(fill="x", padx=40)
        self.pw_entry = tk.Entry(card, font=(FONT, 13), width=24, show="\u2022",
                                  highlightthickness=2, highlightcolor=ACCENT,
                                  highlightbackground=BORDER, relief="flat",
                                  bg="#F9FAFB")
        self.pw_entry.pack(fill="x", padx=40, pady=(4, 10))

        # Remember me
        self.remember_var = tk.BooleanVar(value=False)
        tk.Checkbutton(card, text="Remember me",
                        variable=self.remember_var, bg=BG_CARD, fg=FG,
                        selectcolor="#F9FAFB", activebackground=BG_CARD,
                        font=(FONT, 10)).pack(anchor="w", padx=38, pady=(0, 6))

        # Error label
        self.err_lbl = tk.Label(card, text="", bg=BG_CARD, fg=DANGER,
                                 font=(FONT, 10, "bold"), wraplength=300)
        self.err_lbl.pack(pady=(0, 6))

        # Sign In button
        self.login_btn = tk.Frame(card, bg=ACCENT, cursor="hand2")
        self.login_btn.pack(pady=(0, 10))
        self.login_btn_lbl = tk.Label(self.login_btn, text="  Sign In  ",
                                       bg=ACCENT, fg="#FFFFFF",
                                       font=(FONT, 13, "bold"),
                                       padx=40, pady=10, cursor="hand2")
        self.login_btn_lbl.pack()

        for w in (self.login_btn, self.login_btn_lbl):
            w.bind("<Button-1>", lambda e: self._do_login())
            w.bind("<Enter>", lambda e: self._btn_hover(True))
            w.bind("<Leave>", lambda e: self._btn_hover(False))

        self.pw_entry.bind("<Return>", lambda e: self._do_login())
        self.email_entry.bind("<Return>", lambda e: self.pw_entry.focus_set())

        # Forgot password
        tk.Label(card,
                 text=f"Forgot password? Contact {SUPPORT_EMAIL}",
                 bg=BG_CARD, fg=FG_SEC, font=(FONT, 9)).pack(pady=(2, 0))

        tk.Label(self, text=f"{APP_NAME}  \u00A9 2026  Stamhad Software",
                 bg=BG_PAGE, fg=FG_SEC, font=(FONT, 9)).pack(side="bottom", pady=12)

    def _btn_hover(self, entering):
        c = ACCENT_HV if entering else ACCENT
        self.login_btn.config(bg=c)
        self.login_btn_lbl.config(bg=c)

    def _do_login(self):
        email = self.email_entry.get().strip()
        password = self.pw_entry.get().strip()
        if not email or not password:
            self.err_lbl.config(text="Please enter email and password.")
            return

        self.err_lbl.config(text="Signing in...", fg=FG_SEC)
        self.update()

        def _auth_thread():
            ok, msg, account = auth.authenticate(email, password)
            self.after(0, lambda: self._handle_result(
                ok, msg, account, email, password))

        threading.Thread(target=_auth_thread, daemon=True).start()

    def _handle_result(self, ok, msg, account, email, password):
        if ok:
            uid = account.get("uid", "")
            display_name = (account.get("owner_name") or
                            account.get("restaurant_name") or email)
            role = account.get("role", "restaurant")
            restaurant_name = account.get("restaurant_name", "My Restaurant")

            # Save credentials for auto-login if "Remember me" is checked
            if self.remember_var.get():
                auth.save_session(email, password, restaurant_name)
            else:
                auth.clear_session()

            self.destroy()
            self._on_success(email, display_name, role, uid, restaurant_name)

        elif account and not account.get("enabled", True):
            self.err_lbl.config(
                text=f"Account suspended. Contact {SUPPORT_EMAIL}",
                fg=DANGER)
        else:
            self.err_lbl.config(text=msg, fg=DANGER)


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTO-LOGIN SPLASH  (re-authenticates with Firebase using saved credentials)
# ═══════════════════════════════════════════════════════════════════════════════

class AutoLoginSplash(tk.Tk):
    """
    Small splash shown during auto-login.
    Calls Firebase sign-in with saved credentials.
    If it works -> launches app. If not -> shows login form.
    """

    def __init__(self, session, on_success, on_fail):
        super().__init__()
        self.title(APP_NAME)
        self.configure(bg=BG_PAGE)
        self.geometry("340x240")
        self.resizable(False, False)
        self._session = session
        self._on_success = on_success
        self._on_fail = on_fail

        _set_window_icon(self)

        # Splash: icon + text
        self._splash_icon = _load_icon("icon_dark_64.png", master=self)
        if self._splash_icon:
            tk.Label(self, image=self._splash_icon, bg=BG_PAGE).pack(pady=(24, 6))
        tk.Label(self, text=APP_NAME, bg=BG_PAGE, fg=BG_NAV,
                 font=(FONT, 20, "bold")).pack(pady=(0, 2))
        tk.Label(self, text="by Stamhad Software", bg=BG_PAGE, fg=FG_SEC,
                 font=(FONT, 9)).pack(pady=(0, 8))
        self._status = tk.Label(self, text="Signing in...", bg=BG_PAGE,
                                 fg=FG_SEC, font=(FONT, 11))
        self._status.pack(pady=(0, 10))

        # Start auth in background
        self.after(100, self._try_auto_login)

    def _try_auto_login(self):
        email = self._session["email"]
        password = self._session["password"]

        def _worker():
            ok, msg, account = auth.authenticate(email, password)
            self.after(0, lambda: self._handle(ok, msg, account, password))

        threading.Thread(target=_worker, daemon=True).start()

    def _handle(self, ok, msg, account, password):
        if ok:
            email = account.get("email", self._session.get("email", ""))
            uid = account.get("uid", "")
            display_name = (account.get("owner_name") or
                            account.get("restaurant_name") or email)
            role = account.get("role", "restaurant")
            restaurant_name = account.get("restaurant_name", "My Restaurant")

            # Re-save session with fresh restaurant name
            auth.save_session(email, password, restaurant_name)

            self.destroy()
            self._on_success(email, display_name, role, uid, restaurant_name)
        else:
            # Auto-login failed — clear session, show login form
            print(f"[Auto-login] Failed: {msg}")
            auth.clear_session()
            self.destroy()
            self._on_fail(self._session.get("email", ""))


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def require_login(launch_app_callback):
    """
    Try auto-login first (saved credentials -> Firebase sign-in).
    If no session or auto-login fails -> show the login form.
    Firebase is contacted every launch either way.
    launch_app_callback(email, display_name, role, uid, restaurant_name)
    """
    session = auth.load_session()

    if session:
        # We have saved credentials — try auto-login via Firebase
        def on_fail(email=""):
            login_win = LoginWindow(launch_app_callback, prefill_email=email)
            login_win.mainloop()

        splash = AutoLoginSplash(session, launch_app_callback, on_fail)
        splash.mainloop()
    else:
        # No saved session — straight to login form
        login_win = LoginWindow(launch_app_callback)
        login_win.mainloop()
