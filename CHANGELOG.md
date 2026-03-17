# Stamhad Payroll — Changelog

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
