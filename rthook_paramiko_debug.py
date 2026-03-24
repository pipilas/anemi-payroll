"""Runtime hook — runs before the app starts. Logs paramiko import status."""
import sys
try:
    import paramiko
    print(f"[RTHOOK] paramiko {paramiko.__version__} loaded OK from {paramiko.__file__}")
except ImportError as e:
    print(f"[RTHOOK] paramiko import FAILED: {e}", file=sys.stderr)
    # Try to find what's actually missing
    try:
        import cryptography
        print(f"[RTHOOK] cryptography OK: {cryptography.__version__}")
    except ImportError as e2:
        print(f"[RTHOOK] cryptography FAILED: {e2}", file=sys.stderr)
    try:
        import nacl
        print(f"[RTHOOK] nacl OK")
    except ImportError as e3:
        print(f"[RTHOOK] nacl FAILED: {e3}", file=sys.stderr)
    try:
        import bcrypt
        print(f"[RTHOOK] bcrypt OK: {bcrypt.__version__}")
    except ImportError as e4:
        print(f"[RTHOOK] bcrypt FAILED: {e4}", file=sys.stderr)
    try:
        import cffi
        print(f"[RTHOOK] cffi OK: {cffi.__version__}")
    except ImportError as e5:
        print(f"[RTHOOK] cffi FAILED: {e5}", file=sys.stderr)
