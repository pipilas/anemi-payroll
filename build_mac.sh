#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════════
#  Build Stamhad Payroll — macOS (.app + .dmg)
#  Run from the project root: ./build_mac.sh
# ═══════════════════════════════════════════════════════════════════════════════

set -e

APP_NAME="Stamhad Payroll"
VERSION="1.0.0"
DMG_NAME="StamhadPayroll-${VERSION}-mac"

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  Building ${APP_NAME} v${VERSION} for macOS"
echo "══════════════════════════════════════════════════════════"
echo ""

# ── Step 1: Install build dependencies ──────────────────────────────────────
echo "▶ Installing dependencies..."
pip install pyinstaller reportlab requests flask --quiet

# ── Step 2: Clean previous builds ───────────────────────────────────────────
echo "▶ Cleaning previous builds..."
rm -rf build/ dist/ "${DMG_NAME}.dmg"

# ── Step 3: Build with PyInstaller ──────────────────────────────────────────
echo "▶ Building .app bundle with PyInstaller..."
pyinstaller stamhad_payroll.spec --clean --noconfirm

# Verify .app was created
if [ ! -d "dist/${APP_NAME}.app" ]; then
    echo "❌ Error: .app bundle was not created!"
    exit 1
fi

echo "✅ ${APP_NAME}.app created successfully!"

# ── Step 4: Create DMG ──────────────────────────────────────────────────────
echo "▶ Creating DMG installer..."

# Create a temporary directory for DMG contents
DMG_TEMP="dmg_temp"
rm -rf "${DMG_TEMP}"
mkdir -p "${DMG_TEMP}"

# Copy the .app into the temp directory
cp -R "dist/${APP_NAME}.app" "${DMG_TEMP}/"

# Create a symbolic link to /Applications for drag-and-drop install
ln -s /Applications "${DMG_TEMP}/Applications"

# Create a simple README
cat > "${DMG_TEMP}/README.txt" << 'EOF'
Stamhad Payroll - Installation
═══════════════════════════════

Drag "Stamhad Payroll.app" into the Applications folder.

First launch:
  If macOS blocks the app, go to:
  System Settings → Privacy & Security → Open Anyway

Support: stamhadsoftware@gmail.com
EOF

# Create the DMG using hdiutil
hdiutil create -volname "${APP_NAME}" \
    -srcfolder "${DMG_TEMP}" \
    -ov -format UDZO \
    "dist/${DMG_NAME}.dmg"

# Clean up temp directory
rm -rf "${DMG_TEMP}"

echo ""
echo "══════════════════════════════════════════════════════════"
echo "  ✅ Build Complete!"
echo ""
echo "  .app:  dist/${APP_NAME}.app"
echo "  .dmg:  dist/${DMG_NAME}.dmg"
echo "══════════════════════════════════════════════════════════"
echo ""
