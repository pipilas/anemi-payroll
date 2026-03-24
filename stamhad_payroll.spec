# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Stamhad Payroll
Works for both macOS (.app) and Windows (.exe)
"""

import sys
import os

block_cipher = None

# Force-collect paramiko and its dependencies
from PyInstaller.utils.hooks import collect_all

paramiko_datas, paramiko_binaries, paramiko_hiddenimports = collect_all('paramiko')
nacl_datas, nacl_binaries, nacl_hiddenimports = collect_all('nacl')
bcrypt_datas, bcrypt_binaries, bcrypt_hiddenimports = collect_all('bcrypt')
cffi_datas, cffi_binaries, cffi_hiddenimports = collect_all('cffi')
try:
    SPEC_DIR = os.path.dirname(os.path.abspath(SPEC))
except NameError:
    SPEC_DIR = os.path.abspath('.')

# All Python source files that make up the app
source_files = [
    'payroll_v2.py',
    'payroll_app.py',
    'tax_calculator.py',
    'login_screen.py',
    'auth_manager.py',
    'admin_panel.py',
    'admin_server.py',
    'access_control.py',
    'updater/__init__.py',
    'updater/updater.py',
    'updater/update_dialog.py',
    'updater/version_manager.py',
]

# Data files to bundle (config, tax tables, version info)
data_files = [
    (os.path.join(SPEC_DIR, 'config'), 'config'),
    (os.path.join(SPEC_DIR, 'icons'), 'icons'),
    (os.path.join(SPEC_DIR, 'tax_tables_2025.json'), '.'),
    (os.path.join(SPEC_DIR, 'version.json'), '.'),
    (os.path.join(SPEC_DIR, 'version.txt'), '.'),
]

a = Analysis(
    ['payroll_v2.py'],
    pathex=[],
    binaries=paramiko_binaries + nacl_binaries + bcrypt_binaries + cffi_binaries,
    datas=data_files + paramiko_datas + nacl_datas + bcrypt_datas + cffi_datas,
    hiddenimports=[
        'payroll_app',
        'tax_calculator',
        'login_screen',
        'auth_manager',
        'admin_panel',
        'admin_server',
        'access_control',
        'updater',
        'updater.updater',
        'updater.update_dialog',
        'updater.version_manager',
        'reportlab',
        'reportlab.lib',
        'reportlab.platypus',
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.lib.colors',
        'reportlab.lib.styles',
        'flask',
        'requests',
    ] + paramiko_hiddenimports + nacl_hiddenimports + bcrypt_hiddenimports + cffi_hiddenimports + [
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Windows EXE ──────────────────────────────────────────────────────────────
if sys.platform == 'win32':
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='StamhadPayroll',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,              # No terminal window
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=os.path.join(SPEC_DIR, 'icons', 'stamhad_payroll_icon_dark.ico'),
    )

# ── macOS APP ────────────────────────────────────────────────────────────────
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='StamhadPayroll',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=True,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='StamhadPayroll',
    )

    app = BUNDLE(
        coll,
        name='Stamhad Payroll.app',
        icon=None,                  # Add 'icon.icns' path here if you have one
        bundle_identifier='com.stamhad.payroll',
        info_plist={
            'CFBundleName': 'Stamhad Payroll',
            'CFBundleDisplayName': 'Stamhad Payroll',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': True,
        },
    )
