# Stamhad Payroll — Changelog

## v1.3.13 — March 23, 2026
- **Fix**: Added collect_all for cryptography package in PyInstaller spec
- **Fix**: Runtime debug hook logs exact paramiko import failure on .app launch
- **Debug**: Launch .app from terminal to see `[RTHOOK]` messages showing what fails

## v1.3.12 — March 23, 2026
- **Fix**: Added PyInstaller hook file for paramiko — ensures all submodules collected at freeze time
- **Fix**: hookspath added to spec so PyInstaller discovers the custom hook
- **Fix**: Force-collect paramiko, nacl, bcrypt, cryptography, cffi in build

## v1.3.11 — March 23, 2026
- **Fix**: Paramiko and all SFTP dependencies (bcrypt, pynacl, cryptography, cffi) force-collected in PyInstaller build
- **Fix**: CI workflow explicitly installs all paramiko sub-dependencies
- **Fix**: Better error messages show actual missing module when import fails

## v1.3.0 — March 23, 2026
- **New**: Toast SFTP download — "Download from Toast" button fetches TimeEntries directly from Toast server via SSH
- **New**: Editable preview window shows Employee, Job, Time In, Time Out, Hours before importing — edit times, skip rows
- **New**: SSH key stored per-restaurant in Firebase — set up once, works on all computers automatically
- **New**: Toast SSH Key settings in hamburger menu — browse, upload, and sync SSH keys
- **New**: Tips-only save — enter tips before employee hours are filled (shift totals persist)
- **New**: Tips tab shows all 3 shifts (Morning, Brunch, Dinner) always
- **New**: Editable tip points per employee on Hours tab
- **Fix**: SFTP and manual CSV import both supported (different column formats: In Date/Out Date vs Time In/Time Out)
- **Fix**: Date stripped from SFTP time fields (e.g. "03/22/2026 06:57 AM" → "06:57 AM")
- **Fix**: Trackpad and mouse wheel scrolling fixed across the entire app on macOS
- **Fix**: Points set to 0 persist correctly (no revert to defaults)
- **Fix**: Tips persist when saved without employees (shift total sentinel rows)

## v1.2.24 — March 21, 2026
- **New**: Tips tab shows all 3 shifts (Morning, Brunch, Dinner) always — enter tips before hours are filled
- **New**: Editable tip points per employee on the Hours tab — "Pts" field next to each shift row
- Points auto-populate from position defaults but can be overridden per day
- Changing position dropdown auto-updates points to match the new position
- Points flow into tip distribution calculation on the Tips tab
- **Fix**: Setting points to 0 now persists correctly (no fallback to defaults)

## v1.2.23 — March 20, 2026
- **New**: Editable tip points per employee on the Hours tab — "Pts" field next to each shift row
- Points auto-populate from position defaults but can be overridden per day
- Changing position dropdown auto-updates points to match the new position
- Points flow into tip distribution calculation on the Tips tab
- Points persist through save/load (CSV + Firebase) — setting 0 points stays at 0

## v1.2.22 — March 19, 2026
- **Fix**: Saving a day without redistributing tips no longer wipes existing tips from CSV, cache, and Firebase
- **Fix**: Toast import skips all 0-hour entries (accidental same-time clock in/out like Adalis 11:29 PM)
- **Fix**: Toast import replaces old rows for imported employees instead of creating duplicates

## v1.2.21 — March 17, 2026
- **New**: Week View day cards show separate status indicators for hours (⏱) and tips (💰)
  - ⏱✓ = all hours filled, ⏱⚠ = some hours missing
  - 💰✓ = tips distributed, 💰⚠ = tips not yet distributed

## v1.2.2 — March 17, 2026
- **Fix**: Week View detail tables (FOH Hours, BOH Hours, Tips) now load from Firebase cache instead of CSV files only — data shows consistently with the daily summary cards
- **Toast Import**: Employees still clocked in (no Time Out, 0 hours) are skipped and listed in the import summary
- **Toast Import**: Morning shift auto-selects "Server (morning)" position variant when available

## v1.2.1 — March 17, 2026
- **New**: Prev Week / Next Week navigation on Payroll Report page
- **New**: Prev Week / Next Week navigation on Detailed Payroll page

## v1.2.0 — March 17, 2026
- **New**: Toast POS CSV import — "Import from Toast" button on Today page header
- Smart employee name matching (Last, First → First Last) with fuzzy fallback
- Auto shift detection from clock-in time (before 11:30 AM = Morning, after = Dinner)
- Supports double-shift employees (morning + dinner as separate rows)
- Import summary shows unmatched employee names

## v1.1.52 — March 16, 2026
- Fix: Proper .ico file for Windows taskbar/EXE icon (was SVG renamed to .ico)
- Cleaned up login and splash screen layout
- Icon set on all app windows (Windows .ico + macOS/Linux PNG)

## v1.1.51 — March 16, 2026
- Nav bar: replaced horizontal logo with small icon + text label

## v1.1.5 — March 16, 2026
- App branding with SVG-sourced PNG icons on login, splash, nav bar, PDFs, and window icon
- Logo added to all PDF exports (weekly details, payslips, export all)

## v1.1.4 — March 16, 2026
- **Fix**: Data loss bug — tips/hours entered one day showing $0 the next
  - Immediate Firebase sync on save (with dirty queue fallback)
  - Persistent dirty queue saved to `pending_sync.json` (survives app restart)
  - Smart merge on bulk download preserves local pending data

## v1.1.3 — March 15, 2026
- Main (default) position per employee with multiple positions support
- Default shift set to Dinner for all employees

## v1.1.2 — March 15, 2026
- Offline-first architecture: all data downloaded on login, local cache with background sync
- Background sync to Firebase every 15 seconds
- App works without internet connection

## v1.0.0 — Initial Release
- Payroll & tip management desktop application
- Employee management (FOH/BOH, positions, wages)
- Daily hours and tips entry with shift support
- Weekly payroll reports with labor cost tracking
- Detailed payroll with tax calculations
- PDF export for payslips
- CSV export for weekly data
- Firebase cloud sync
