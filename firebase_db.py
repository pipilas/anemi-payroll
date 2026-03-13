"""
Firebase Realtime Database — data layer for Stamhad Payroll.

Global (shared) data:
    /tax_tables                         — tax brackets/rates for all restaurants

Per-restaurant data:
    /restaurant_data/{uid}/employees
    /restaurant_data/{uid}/positions
    /restaurant_data/{uid}/weeks/{week_date}/foh_hours
    /restaurant_data/{uid}/weeks/{week_date}/boh_hours
    /restaurant_data/{uid}/weeks/{week_date}/tips

Each restaurant (uid) is fully isolated.
Falls back to local files if Firebase is unreachable.
"""

import json
import urllib.request
import urllib.error
import traceback

from auth_manager import _db_url


class FirebaseDB:
    """
    Firebase Realtime Database client for a single restaurant.
    Pass the restaurant's Firebase Auth UID to scope all data.
    """

    def __init__(self, uid):
        self.uid = uid
        self._base = f"restaurant_data/{uid}"

    # ══════════════════════════════════════════════════════════════════════════
    #  LOW-LEVEL HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _get(self, path):
        """GET data from Firebase. Returns parsed JSON or None."""
        url = f"{_db_url()}/{self._base}/{path}.json"
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except Exception as e:
            print(f"[FirebaseDB] GET {path} failed: {e}")
            return None

    def _put(self, path, data):
        """PUT (overwrite) data at a Firebase path. Returns True on success."""
        url = f"{_db_url()}/{self._base}/{path}.json"
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="PUT",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return True
        except Exception as e:
            print(f"[FirebaseDB] PUT {path} failed: {e}")
            return False

    def _patch(self, path, data):
        """PATCH (merge) data at a Firebase path. Returns True on success."""
        url = f"{_db_url()}/{self._base}/{path}.json"
        payload = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="PATCH",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return True
        except Exception as e:
            print(f"[FirebaseDB] PATCH {path} failed: {e}")
            return False

    def _delete(self, path):
        """DELETE data at a Firebase path."""
        url = f"{_db_url()}/{self._base}/{path}.json"
        req = urllib.request.Request(url, method="DELETE")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return True
        except Exception:
            return False

    # ══════════════════════════════════════════════════════════════════════════
    #  EMPLOYEES
    # ══════════════════════════════════════════════════════════════════════════

    def load_employees(self):
        """Load employees list from Firebase. Returns list or None on failure."""
        data = self._get("employees")
        if data is None:
            return None
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.values())
        return []

    def save_employees(self, employees):
        """Save full employees list to Firebase. Returns True on success."""
        return self._put("employees", employees)

    # ══════════════════════════════════════════════════════════════════════════
    #  POSITIONS
    # ══════════════════════════════════════════════════════════════════════════

    def load_positions(self):
        """Load positions list from Firebase. Returns list or None on failure."""
        data = self._get("positions")
        if data is None:
            return None
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return list(data.values())
        return []

    def save_positions(self, positions):
        """Save full positions list to Firebase. Returns True on success."""
        return self._put("positions", positions)

    # ══════════════════════════════════════════════════════════════════════════
    #  WEEKLY DATA (hours + tips)
    # ══════════════════════════════════════════════════════════════════════════

    def save_week_day(self, week_date, day_name, foh_rows, boh_rows, tip_rows):
        """
        Save a single day's data for a given week.
        week_date: e.g. "2026-03-09" (Monday of the week)
        day_name: e.g. "Monday", "Tuesday", etc.
        """
        week_key = week_date.replace("-", "_")
        day_data = {
            "foh_hours": foh_rows,
            "boh_hours": boh_rows,
            "tips": tip_rows,
        }
        return self._put(f"weeks/{week_key}/days/{day_name}", day_data)

    def load_week_day(self, week_date, day_name):
        """
        Load a single day's data. Returns (foh_rows, boh_rows, tip_rows).
        Returns (None, None, None) on failure (so caller uses local fallback).
        """
        week_key = week_date.replace("-", "_")
        data = self._get(f"weeks/{week_key}/days/{day_name}")
        if data is None:
            return None, None, None
        foh = data.get("foh_hours", []) if isinstance(data, dict) else []
        boh = data.get("boh_hours", []) if isinstance(data, dict) else []
        tips = data.get("tips", []) if isinstance(data, dict) else []
        # Firebase may return dicts instead of lists
        if isinstance(foh, dict):
            foh = list(foh.values())
        if isinstance(boh, dict):
            boh = list(boh.values())
        if isinstance(tips, dict):
            tips = list(tips.values())
        return foh, boh, tips

    # ══════════════════════════════════════════════════════════════════════════
    #  MIGRATION: upload local data to Firebase (one-time)
    # ══════════════════════════════════════════════════════════════════════════

    def migrate_if_needed(self, local_employees, local_positions):
        """
        If Firebase has no data for this restaurant yet, upload local data.
        This handles the first-time migration from local files to Firebase.
        Returns True if migration happened, False if Firebase already had data.
        """
        remote_emp = self._get("employees")
        if remote_emp is not None and remote_emp:
            return False  # Firebase already has data — no migration needed

        print(f"[FirebaseDB] Migrating local data to Firebase for uid={self.uid[:8]}...")

        if local_employees:
            self.save_employees(local_employees)
            print(f"[FirebaseDB]   Uploaded {len(local_employees)} employees")

        if local_positions:
            self.save_positions(local_positions)
            print(f"[FirebaseDB]   Uploaded {len(local_positions)} positions")

        return True


# ══════════════════════════════════════════════════════════════════════════════
#  GLOBAL TAX TABLES (shared across all restaurants)
# ══════════════════════════════════════════════════════════════════════════════

def load_tax_tables_from_firebase():
    """
    Load tax tables from Firebase (global, not per-restaurant).
    Returns the tax tables dict, or None on failure.
    """
    url = f"{_db_url()}/tax_tables.json"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data if data else None
    except Exception as e:
        print(f"[FirebaseDB] Load tax tables failed: {e}")
        return None


def save_tax_tables_to_firebase(tables):
    """
    Save tax tables to Firebase (global, not per-restaurant).
    Only admin should call this.
    """
    url = f"{_db_url()}/tax_tables.json"
    payload = json.dumps(tables).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="PUT",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return True
    except Exception as e:
        print(f"[FirebaseDB] Save tax tables failed: {e}")
        return False
