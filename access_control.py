"""
Client-side Access Control
Generates a unique device ID, checks the admin server for permission,
and provides a Tkinter lock screen if access is denied.
"""

import os, json, uuid, hashlib, platform, threading, time
import tkinter as tk
import requests

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
ACCESS_FILE = os.path.join(CONFIG_DIR, "access.json")

# ── Device ID ───────────────────────────────────────────────────────────────

def _get_device_id():
    """Generate a stable, unique device fingerprint."""
    raw = f"{platform.node()}-{platform.machine()}-{uuid.getnode()}"
    return hashlib.sha256(raw.encode()).hexdigest()

# ── Access config persistence ──────────────────────────────────────────────

def _load_access_config():
    if os.path.exists(ACCESS_FILE):
        with open(ACCESS_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_access_config(cfg):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(ACCESS_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

# ── Server check ────────────────────────────────────────────────────────────

def check_access(server_url, api_key):
    """
    Returns (allowed: bool, reason: str).
    Tries the server; if unreachable, falls back to cached status.
    """
    device_id = _get_device_id()
    cfg = _load_access_config()

    try:
        resp = requests.post(
            f"{server_url.rstrip('/')}/api/check",
            json={
                "device_id": device_id,
                "api_key": api_key,
                "label": platform.node(),
            },
            timeout=8,
        )
        data = resp.json()
        # cache the result
        cfg["last_status"] = data.get("access", False)
        cfg["last_check"] = time.time()
        cfg["device_id"] = device_id
        _save_access_config(cfg)

        if data.get("access"):
            return True, "granted"
        return False, data.get("reason", "denied")

    except Exception:
        # server unreachable – use cached status (grace period: 7 days)
        if cfg.get("last_status") and (time.time() - cfg.get("last_check", 0)) < 604800:
            return True, "cached_grant"
        return False, "server_unreachable"


# ── Lock Screen UI ──────────────────────────────────────────────────────────

class AccessGate:
    """
    Shows a lock screen. Retries every 15 seconds.
    When access is granted, calls `on_granted()` callback.
    """

    def __init__(self, root, server_url, api_key, on_granted):
        self.root = root
        self.server_url = server_url
        self.api_key = api_key
        self.on_granted = on_granted
        self._running = True

        self.frame = tk.Frame(root, bg="#0F172A")
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        # center container
        inner = tk.Frame(self.frame, bg="#0F172A")
        inner.place(relx=0.5, rely=0.45, anchor="center")

        tk.Label(inner, text="🔒", font=("Arial", 48), bg="#0F172A", fg="#E2E8F0").pack()
        tk.Label(
            inner, text="Access Required",
            font=("Helvetica", 22, "bold"), bg="#0F172A", fg="#E2E8F0"
        ).pack(pady=(10, 5))

        self.status_label = tk.Label(
            inner, text="Checking access...",
            font=("Helvetica", 12), bg="#0F172A", fg="#94A3B8"
        )
        self.status_label.pack(pady=(0, 10))

        self.device_label = tk.Label(
            inner, text=f"Device: {_get_device_id()[:16]}...",
            font=("Courier", 10), bg="#0F172A", fg="#475569"
        )
        self.device_label.pack(pady=(0, 20))

        retry_btn = tk.Button(
            inner, text="Retry Now", font=("Helvetica", 11, "bold"),
            bg="#4F46E5", fg="#FFFFFF", relief="flat", padx=20, pady=8,
            cursor="hand2", command=self._manual_check,
        )
        retry_btn.pack()

        self._schedule_check()

    def _schedule_check(self):
        if not self._running:
            return
        threading.Thread(target=self._do_check, daemon=True).start()

    def _do_check(self):
        allowed, reason = check_access(self.server_url, self.api_key)
        if not self._running:
            return
        if allowed:
            self.root.after(0, self._unlock)
        else:
            msg = {
                "pending_approval": "Waiting for admin approval...",
                "denied": "Access has been denied by the admin.",
                "server_unreachable": "Cannot reach the server. Retrying...",
                "invalid_key": "Invalid API key. Check your config.",
            }.get(reason, "Access denied.")
            self.root.after(0, lambda: self.status_label.config(text=msg))
            # auto-retry in 15 seconds
            if self._running:
                self.root.after(15000, self._schedule_check)

    def _manual_check(self):
        self.status_label.config(text="Checking...")
        threading.Thread(target=self._do_check, daemon=True).start()

    def _unlock(self):
        self._running = False
        self.frame.destroy()
        self.on_granted()
