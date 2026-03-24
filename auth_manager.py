"""
Stamhad Payroll — Firebase Authentication Manager
Uses Firebase Authentication REST API for sign-in / sign-up.
Uses Firebase Realtime Database for account metadata (restaurant name, plan, enabled, etc.).

Firebase Auth: handles email + password (Identity Toolkit API)
Firebase Realtime DB structure:
  restaurants/
    {uid}/                         # Firebase Auth UID
      email: "owner@example.com"
      restaurant_name: "Restaurant Name"
      owner_name: "Owner Full Name"
      app_name: "Anemi"
      plan: "Standard"
      notes: ""
      enabled: true/false
      role: "admin" | "restaurant"
      created_at: "iso-timestamp"
      last_login: ""

Admin creates all accounts — NO self-signup.
Local session file: config/session.json  (stores refresh token for auto-login)
"""

import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"

# Session file lives in user's home dir so it survives app updates
import platform as _plat
if _plat.system() == "Darwin":
    _USER_DATA_DIR = Path.home() / "Library" / "Application Support" / "StamhadPayroll"
elif _plat.system() == "Windows":
    _USER_DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "StamhadPayroll"
else:
    _USER_DATA_DIR = Path.home() / ".stamhad_payroll"
_USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

SESSION_FILE = _USER_DATA_DIR / "session.json"

# Migrate old session from bundled config dir if it exists
_OLD_SESSION = CONFIG_DIR / "session.json"
if _OLD_SESSION.exists() and not SESSION_FILE.exists():
    try:
        import shutil
        shutil.copy2(_OLD_SESSION, SESSION_FILE)
    except Exception:
        pass
FIREBASE_CONFIG_FILE = CONFIG_DIR / "firebase_config.json"

SUPPORT_EMAIL = "stamhadsoftware@gmail.com"

# Firebase Auth REST API base
_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1"

# ── Hardcoded Firebase config (no setup screen needed) ─────────────────────
_FIREBASE_DB_URL = "https://payroll-be52a-default-rtdb.firebaseio.com"
_FIREBASE_API_KEY = "AIzaSyB_goGoZ4aOsvPBNRVxW9CxftQEewHAQtc"


# ═══════════════════════════════════════════════════════════════════════════════
#  FIREBASE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

def load_firebase_config():
    """Return the hardcoded Firebase config. No file needed."""
    return {
        "database_url": _FIREBASE_DB_URL,
        "api_key": _FIREBASE_API_KEY,
    }


def _db_url():
    """Get the Firebase Realtime Database URL."""
    return _FIREBASE_DB_URL


def _api_key():
    """Get the Firebase Web API Key."""
    return _FIREBASE_API_KEY


# ═══════════════════════════════════════════════════════════════════════════════
#  FIREBASE AUTH REST API  (Identity Toolkit)
# ═══════════════════════════════════════════════════════════════════════════════

def _auth_request(endpoint, payload):
    """
    POST to Firebase Auth REST API.
    endpoint: e.g. 'accounts:signInWithPassword'
    Returns parsed JSON response.
    """
    url = f"{_AUTH_BASE}/{endpoint}?key={_api_key()}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        try:
            err = json.loads(body)
            msg = err.get("error", {}).get("message", body)
        except Exception:
            msg = body
        raise ConnectionError(f"Firebase Auth error: {msg}")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Cannot reach Firebase: {e.reason}")


def firebase_sign_in(email, password):
    """
    Sign in with email + password via Firebase Auth.
    Returns dict with idToken, localId (uid), email, refreshToken, etc.
    """
    return _auth_request("accounts:signInWithPassword", {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    })


def firebase_sign_up(email, password):
    """
    Create a new user in Firebase Auth.
    Returns dict with idToken, localId (uid), email, etc.
    """
    return _auth_request("accounts:signUp", {
        "email": email,
        "password": password,
        "returnSecureToken": True,
    })


def firebase_get_user(id_token):
    """
    Get user info from Firebase Auth using idToken.
    Returns dict with users list.
    """
    return _auth_request("accounts:lookup", {
        "idToken": id_token,
    })


def firebase_change_password(id_token, new_password):
    """Change password for the user identified by idToken."""
    return _auth_request("accounts:update", {
        "idToken": id_token,
        "password": new_password,
        "returnSecureToken": True,
    })


def firebase_delete_user(id_token):
    """Delete a user from Firebase Auth."""
    return _auth_request("accounts:delete", {
        "idToken": id_token,
    })


# ═══════════════════════════════════════════════════════════════════════════════
#  FIREBASE REALTIME DATABASE HELPERS  (for metadata)
# ═══════════════════════════════════════════════════════════════════════════════

def _firebase_get(path):
    """GET data from Firebase Realtime Database."""
    url = f"{_db_url()}/{path}.json"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        raise ConnectionError(f"Firebase DB GET error {e.code}: {body}")
    except urllib.error.URLError as e:
        raise ConnectionError(f"Cannot reach Firebase: {e.reason}")


def _firebase_put(path, data):
    """PUT (overwrite) data at a Firebase path."""
    url = f"{_db_url()}/{path}.json"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="PUT",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        raise ConnectionError(f"Firebase DB PUT error {e.code}: {body}")


def _firebase_patch(path, data):
    """PATCH (update) data at a Firebase path."""
    url = f"{_db_url()}/{path}.json"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="PATCH",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        raise ConnectionError(f"Firebase DB PATCH error {e.code}: {body}")


def _firebase_delete(path):
    """DELETE data at a Firebase path."""
    url = f"{_db_url()}/{path}.json"
    req = urllib.request.Request(url, method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _email_to_key(email):
    """Convert email to Firebase-safe key ('.' → ',')."""
    return email.strip().lower().replace(".", ",")


def _uid_from_email(email):
    """Look up a UID by email in the DB index."""
    key = _email_to_key(email)
    return _firebase_get(f"email_index/{key}")


# ═══════════════════════════════════════════════════════════════════════════════
#  RESTAURANT ACCOUNT MANAGEMENT (admin only)
# ═══════════════════════════════════════════════════════════════════════════════

def create_restaurant_account(email, password, restaurant_name="",
                               owner_name="", app_name="Anemi",
                               plan="Standard", notes="", enabled=True,
                               role="restaurant"):
    """
    Create a new restaurant account:
    1. Create user in Firebase Auth (email + password)
    2. Store metadata in Realtime DB under restaurants/{uid}
    3. Store email→uid index for lookups
    """
    email = email.strip().lower()

    # Step 1: Create in Firebase Auth
    auth_result = firebase_sign_up(email, password)
    uid = auth_result["localId"]

    # Step 2: Store metadata in Realtime DB
    account_data = {
        "email": email,
        "restaurant_name": restaurant_name or email,
        "owner_name": owner_name or "",
        "app_name": app_name or "Anemi",
        "plan": plan or "Standard",
        "notes": notes or "",
        "enabled": enabled,
        "role": role,
        "created_at": datetime.now().isoformat(),
        "last_login": "",
    }
    _firebase_put(f"restaurants/{uid}", account_data)

    # Step 3: Email → UID index for lookups
    _firebase_put(f"email_index/{_email_to_key(email)}", uid)

    return account_data


def set_account_enabled(uid, enabled=True):
    """Enable or disable a restaurant account by UID."""
    _firebase_patch(f"restaurants/{uid}", {"enabled": enabled})


def set_account_enabled_by_email(email, enabled=True):
    """Enable or disable by email (looks up UID first)."""
    uid = _uid_from_email(email)
    if not uid:
        raise ValueError(f"No account found for {email}")
    set_account_enabled(uid, enabled)


def list_restaurants():
    """List all restaurant accounts from Realtime DB."""
    data = _firebase_get("restaurants")
    return data or {}


def get_restaurant_by_uid(uid):
    """Get a single restaurant account by UID."""
    return _firebase_get(f"restaurants/{uid}")


def get_restaurant_by_email(email):
    """Get restaurant metadata by email."""
    uid = _uid_from_email(email)
    if not uid:
        return None
    data = _firebase_get(f"restaurants/{uid}")
    if data:
        data["uid"] = uid
    return data


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTHENTICATION  (uses Firebase Auth, then checks DB metadata)
# ═══════════════════════════════════════════════════════════════════════════════

def authenticate(email, password):
    """
    Sign in via Firebase Auth, then check enabled flag in Realtime DB.
    Returns (success: bool, message: str, account_data: dict|None)
    account_data includes 'uid', 'id_token', 'refresh_token' on success.
    """
    email = email.strip().lower()

    # Step 1: Firebase Auth sign-in
    try:
        auth_result = firebase_sign_in(email, password)
    except ConnectionError as e:
        err_msg = str(e)
        if "EMAIL_NOT_FOUND" in err_msg or "INVALID_PASSWORD" in err_msg:
            return False, "Invalid email or password.", None
        if "INVALID_LOGIN_CREDENTIALS" in err_msg:
            return False, "Invalid email or password.", None
        if "USER_DISABLED" in err_msg:
            return (False,
                    "Your account has been suspended.\n"
                    f"Contact {SUPPORT_EMAIL} for assistance.",
                    None)
        return False, f"Connection error: {e}", None

    uid = auth_result["localId"]
    id_token = auth_result.get("idToken", "")
    refresh_token = auth_result.get("refreshToken", "")

    # Step 2: Get metadata from Realtime DB
    try:
        account = _firebase_get(f"restaurants/{uid}")
    except ConnectionError:
        account = None

    if account is None:
        # Auth succeeded but no DB record — create a basic one
        account = {
            "email": email,
            "restaurant_name": email,
            "owner_name": "",
            "role": "restaurant",
            "enabled": True,
        }

    # Step 3: Check enabled flag
    if not account.get("enabled", True):
        return (False,
                "Your account has been suspended.\n"
                f"Contact {SUPPORT_EMAIL} for assistance.",
                account)

    # Step 4: Update last login
    try:
        _firebase_patch(f"restaurants/{uid}", {
            "last_login": datetime.now().isoformat()
        })
    except Exception:
        pass

    # Attach auth tokens to account data
    account["uid"] = uid
    account["id_token"] = id_token
    account["refresh_token"] = refresh_token

    return True, "Login successful.", account


def check_account_active(uid):
    """
    Check if an account is still enabled (for periodic session checks).
    Returns (is_active: bool, message: str)
    """
    try:
        account = _firebase_get(f"restaurants/{uid}")
    except ConnectionError:
        return True, "offline"

    if account is None:
        return False, "Account no longer exists."

    if not account.get("enabled", True):
        return False, "Your account has been suspended."

    return True, "active"


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION PERSISTENCE  (saves credentials for auto-login)
#  Stores email + base64-encoded password locally.
#  On every launch, calls Firebase Auth sign-in with these credentials,
#  so authentication happens with Firebase every single time.
# ═══════════════════════════════════════════════════════════════════════════════

import base64


def save_session(email, password, restaurant_name=""):
    """Save credentials + restaurant name for auto-login next time."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    session = {
        "email": email.strip().lower(),
        "pw": base64.b64encode(password.encode("utf-8")).decode("ascii"),
        "restaurant_name": restaurant_name,
    }
    with open(SESSION_FILE, "w") as f:
        json.dump(session, f)


def load_session():
    """Load saved session. Returns dict with email, password, restaurant_name or None."""
    if not SESSION_FILE.exists():
        return None
    try:
        with open(SESSION_FILE, "r") as f:
            data = json.load(f)
        if data.get("email") and data.get("pw"):
            return {
                "email": data["email"],
                "password": base64.b64decode(data["pw"]).decode("utf-8"),
                "restaurant_name": data.get("restaurant_name", ""),
            }
        return None
    except Exception:
        return None


def clear_session():
    """Delete saved session (sign out)."""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import sys

    def usage():
        print("Usage:")
        print("  python auth_manager.py add <email> <password> <restaurant_name> <owner_name> [plan]")
        print("  python auth_manager.py disable <email>")
        print("  python auth_manager.py enable <email>")
        print("  python auth_manager.py list")
        print("  python auth_manager.py test <email> <password>")

    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "add" and len(sys.argv) >= 6:
        email, pw = sys.argv[2], sys.argv[3]
        rest_name = sys.argv[4]
        owner = sys.argv[5]
        plan = sys.argv[6] if len(sys.argv) > 6 else "Standard"
        create_restaurant_account(email, pw, rest_name, owner, plan=plan)
        print(f"Restaurant account '{email}' created ({rest_name}).")

    elif cmd == "disable" and len(sys.argv) >= 3:
        set_account_enabled_by_email(sys.argv[2], False)
        print(f"Account '{sys.argv[2]}' disabled.")

    elif cmd == "enable" and len(sys.argv) >= 3:
        set_account_enabled_by_email(sys.argv[2], True)
        print(f"Account '{sys.argv[2]}' enabled.")

    elif cmd == "list":
        restaurants = list_restaurants()
        if not restaurants:
            print("No restaurant accounts found.")
        for uid, data in restaurants.items():
            status = "ENABLED" if data.get("enabled") else "DISABLED"
            print(f"  {data.get('email', uid):30s} {data.get('restaurant_name', ''):20s} "
                  f"{data.get('plan', 'Standard'):10s} [{status}]")

    elif cmd == "test" and len(sys.argv) >= 4:
        ok, msg, _ = authenticate(sys.argv[2], sys.argv[3])
        print(f"{'SUCCESS' if ok else 'FAILED'}: {msg}")

    else:
        usage()
