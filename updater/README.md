# Universal Auto-Update System

Drop-in auto-update package for Python tkinter desktop apps.
Checks GitHub for new versions, shows a clean update dialog, downloads the installer, verifies it, and runs it.

---

## Quick Integration (5 lines)

```python
from updater import Updater

updater = Updater(
    current_version="1.0.0",
    github_username="pipilas",
    github_repo="anemi-payroll",
    app_name="Stamhad Payroll"
)

# Non-blocking background check — shows popup only if update found
updater.check_and_prompt(parent_window=root)
```

---

## How It Works

1. On app launch, `check_and_prompt()` runs a background thread
2. Fetches `version.json` from your GitHub repo (raw.githubusercontent.com)
3. Compares local version (from `version.txt`) with remote version
4. If update available → shows a clean dialog with release notes
5. User clicks "Update Now" → downloads installer with progress bar
6. Verifies SHA256 checksum → launches installer → exits app

---

## Files

| File | Purpose |
|---|---|
| `updater.py` | Main update logic (check, download, install) |
| `update_dialog.py` | Tkinter UI (update popup, download progress) |
| `version_manager.py` | Version parsing & comparison |
| `__init__.py` | Package exports |

---

## version.json (on GitHub)

Place this in your repo root (`main` branch):

```json
{
  "latest_version": "1.2.0",
  "minimum_version": "1.0.0",
  "release_date": "2026-03-13",
  "download_url": "https://github.com/pipilas/anemi-payroll/releases/download/v1.2.0/StamhadPayroll.exe",
  "release_notes": "- Fixed tip calculation bug\n- Added PDF export\n- Improved speed",
  "mandatory": false,
  "checksum_sha256": "paste_sha256_hash_here"
}
```

### Fields

- `latest_version` — newest available version
- `minimum_version` — if user is below this, **force update** regardless of `mandatory`
- `download_url` — direct link to the installer on GitHub Releases
- `release_notes` — shown in the update dialog (use `\n` for line breaks)
- `mandatory` — if `true`, user **cannot skip** the update
- `checksum_sha256` — SHA256 hash of the installer file (integrity check)

---

## How to Release a New Version

### Step 1 — Update version in your code

Edit `version.txt`:
```
1.2.0
```

### Step 2 — Build the installer

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "StamhadPayroll" payroll_v2.py
# Creates: dist/StamhadPayroll.exe
```

### Step 3 — Get the SHA256 checksum

**Windows PowerShell:**
```powershell
Get-FileHash dist\StamhadPayroll.exe -Algorithm SHA256
```

**Mac/Linux:**
```bash
shasum -a 256 dist/StamhadPayroll.exe
```

### Step 4 — Create GitHub Release

1. Go to your GitHub repo → Releases → "Draft a new release"
2. Tag: `v1.2.0`
3. Title: `Stamhad Payroll v1.2.0`
4. Description: paste your release notes
5. Upload: `dist/StamhadPayroll.exe`
6. Click **Publish release**

### Step 5 — Update version.json in your repo

```json
{
  "latest_version": "1.2.0",
  "minimum_version": "1.0.0",
  "release_date": "2026-03-13",
  "download_url": "https://github.com/pipilas/anemi-payroll/releases/download/v1.2.0/StamhadPayroll.exe",
  "release_notes": "- Fixed tip calculation bug\n- Added PDF export",
  "mandatory": false,
  "checksum_sha256": "paste_the_hash_here"
}
```

### Step 6 — Commit and push

```bash
git add version.json
git commit -m "Release v1.2.0"
git push
```

Done! All existing installs will see the update on next launch.

---

## Mandatory vs Optional Updates

| Scenario | Behavior |
|---|---|
| `mandatory: false` | Shows "Update Now" + "Remind Me Later" |
| `mandatory: true` | Shows "Update Now — Required" only. Closing exits the app. |
| Current version < `minimum_version` | Treated as mandatory regardless of flag |

---

## Error Handling

| Situation | Behavior |
|---|---|
| No internet | Silently skips, no error shown |
| GitHub unreachable | Silently skips |
| Download fails | Shows error with "Retry" button |
| Checksum mismatch | Shows "Download corrupted — please try again" |
| Partial download | Checksum will fail → shows error |

---

## Platform Support

- **Windows** (primary) — launches `.exe` installer
- **macOS** — uses `open` command for `.dmg` / `.pkg`
- **Linux** — uses `xdg-open` for `.AppImage` / `.deb`
