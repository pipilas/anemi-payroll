"""PyInstaller hook for paramiko — ensures all submodules are collected."""
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = collect_all('paramiko')
hiddenimports += collect_submodules('paramiko')
hiddenimports += collect_submodules('nacl')
hiddenimports += collect_submodules('bcrypt')
hiddenimports += collect_submodules('cryptography')
hiddenimports += collect_submodules('cffi')
