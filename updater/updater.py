"""
Updater — checks GitHub for new versions, downloads and installs updates.
Works with any Python tkinter app. All app-specific values passed as parameters.
"""

import json
import hashlib
import tempfile
import subprocess
import sys
import os
import threading
import urllib.request
import urllib.error
from pathlib import Path

from .version_manager import get_version, compare_versions, should_update


class Updater:
    """
    Universal auto-updater for Python desktop apps.

    Usage:
        updater = Updater(
            current_version="1.0.0",
            github_username="pipilas",
            github_repo="anemi-payroll",
            app_name="Stamhad Payroll"
        )
        updater.check_and_prompt(parent_window=root)
    """

    def __init__(self, current_version=None, github_username="", github_repo="",
                 app_name="App", version_file=None):
        self.current_version = current_version or get_version(version_file)
        self.github_username = github_username
        self.github_repo = github_repo
        self.app_name = app_name
        self._version_url = (
            f"https://raw.githubusercontent.com/"
            f"{github_username}/{github_repo}/main/version.json"
        )

    def check_for_updates(self):
        """
        Check GitHub for new version. Returns dict with update info.
        Raises ConnectionError on network failure.
        """
        try:
            req = urllib.request.Request(self._version_url, method="GET")
            req.add_header("User-Agent", f"{self.app_name}-Updater")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            raise ConnectionError(f"Cannot check for updates: {e}")

        latest = data.get("latest_version", "0.0.0")
        minimum = data.get("minimum_version", "0.0.0")
        mandatory = data.get("mandatory", False)

        # Force mandatory if current is below minimum
        if compare_versions(self.current_version, minimum) < 0:
            mandatory = True

        update_available = should_update(self.current_version, latest, minimum)

        return {
            "update_available": update_available,
            "latest_version": latest,
            "current_version": self.current_version,
            "minimum_version": minimum,
            "mandatory": mandatory,
            "release_notes": data.get("release_notes", ""),
            "release_date": data.get("release_date", ""),
            "download_url": data.get("download_url", ""),
            "checksum": data.get("checksum_sha256", ""),
        }

    def download_update(self, url, checksum="", progress_callback=None):
        """
        Download installer to temp folder, verify SHA256 checksum.
        progress_callback(bytes_downloaded, total_bytes) called periodically.
        Returns path to downloaded file.
        """
        if not url:
            raise ValueError("No download URL provided.")

        filename = url.split("/")[-1] or "update_installer"
        download_path = Path(tempfile.gettempdir()) / filename

        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("User-Agent", f"{self.app_name}-Updater")
            resp = urllib.request.urlopen(req, timeout=120)
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            raise ConnectionError(f"Download failed: {e}")

        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        chunk_size = 65536

        sha = hashlib.sha256()
        with open(download_path, "wb") as f:
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                sha.update(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    try:
                        progress_callback(downloaded, total)
                    except Exception:
                        pass

        resp.close()

        # Verify checksum
        if checksum:
            actual = sha.hexdigest()
            if actual.lower() != checksum.lower():
                try:
                    download_path.unlink()
                except Exception:
                    pass
                raise ValueError(
                    f"Checksum mismatch.\n"
                    f"Expected: {checksum}\n"
                    f"Got: {actual}\n"
                    f"Download may be corrupted — please try again."
                )

        return str(download_path)

    def install_update(self, installer_path):
        """Launch the installer and exit the current app."""
        if not os.path.exists(installer_path):
            raise FileNotFoundError(f"Installer not found: {installer_path}")

        if sys.platform == "win32":
            subprocess.Popen([installer_path], shell=True)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", installer_path])
        else:
            subprocess.Popen(["xdg-open", installer_path])

        sys.exit(0)

    def is_mandatory_update(self, server_data):
        """Returns True if the update is mandatory or below minimum version."""
        if server_data.get("mandatory", False):
            return True
        minimum = server_data.get("minimum_version", "0.0.0")
        if compare_versions(self.current_version, minimum) < 0:
            return True
        return False

    def check_and_prompt(self, parent_window=None):
        """
        Check for updates in a background thread.
        If update found, shows the update dialog.
        Never blocks or slows down app launch.
        If no internet or check fails, silently skips.
        """
        def _worker():
            try:
                result = self.check_for_updates()
            except Exception:
                return  # Silently skip

            if not result.get("update_available"):
                return

            # Schedule dialog on main thread
            if parent_window:
                delay = 50 if result.get("mandatory") else 500
                try:
                    parent_window.after(delay, lambda: _show(result))
                except Exception:
                    pass

        def _show(result):
            try:
                from .update_dialog import show_update_dialog
                show_update_dialog(parent_window, self, result)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()
