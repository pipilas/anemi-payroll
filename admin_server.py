"""
Admin Server – Manual Access Control Panel
Run this on your machine to manage which app instances are allowed to run.
Usage:  python admin_server.py
Then open http://localhost:5050 in your browser.
"""

import sqlite3, os, secrets, hashlib
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "access_control.db")

app = Flask(__name__)

# ── database ────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            device_id   TEXT PRIMARY KEY,
            label       TEXT DEFAULT '',
            granted     INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admin (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            api_key     TEXT NOT NULL
        )
    """)
    # create default API key if none exists
    row = conn.execute("SELECT api_key FROM admin WHERE id = 1").fetchone()
    if not row:
        key = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO admin (id, api_key) VALUES (1, ?)", (key,))
        print(f"\n{'='*60}")
        print(f"  ADMIN API KEY (save this, clients need it):")
        print(f"  {key}")
        print(f"{'='*60}\n")
    else:
        print(f"\n  Admin API Key: {row['api_key']}\n")
    conn.commit()
    conn.close()

# ── API endpoints (called by the payroll app) ───────────────────────────────

@app.route("/api/check", methods=["POST"])
def api_check():
    """Client calls this on startup to see if access is granted."""
    data = request.get_json(force=True)
    device_id = data.get("device_id", "")
    api_key = data.get("api_key", "")

    conn = get_db()

    # verify api key
    row = conn.execute("SELECT api_key FROM admin WHERE id = 1").fetchone()
    if not row or row["api_key"] != api_key:
        conn.close()
        return jsonify({"access": False, "reason": "invalid_key"}), 403

    # look up device
    dev = conn.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    if not dev:
        # auto-register new devices as pending (denied by default)
        conn.execute(
            "INSERT INTO devices (device_id, label, granted) VALUES (?, ?, 0)",
            (device_id, data.get("label", "Unknown Device")),
        )
        conn.commit()
        conn.close()
        return jsonify({"access": False, "reason": "pending_approval"})

    conn.close()
    if dev["granted"]:
        return jsonify({"access": True})
    else:
        return jsonify({"access": False, "reason": "denied"})


# ── Admin web panel ─────────────────────────────────────────────────────────

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Access Control Panel</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #0F172A; color: #E2E8F0; min-height: 100vh; }
  .wrap { max-width: 900px; margin: 0 auto; padding: 2rem 1rem; }
  h1 { font-size: 1.5rem; margin-bottom: .5rem; color: #818CF8; }
  .subtitle { color: #64748B; margin-bottom: 2rem; font-size: .9rem; }
  .key-box { background: #1E293B; border: 1px solid #334155; border-radius: 8px;
             padding: 1rem; margin-bottom: 2rem; font-family: monospace; font-size: .85rem;
             word-break: break-all; }
  .key-box span { color: #94A3B8; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: .75rem 1rem; color: #94A3B8; font-weight: 500;
       font-size: .8rem; text-transform: uppercase; border-bottom: 1px solid #1E293B; }
  td { padding: .75rem 1rem; border-bottom: 1px solid #1E293B; font-size: .9rem; }
  tr:hover { background: #1E293B; }
  .status { display: inline-block; padding: 2px 10px; border-radius: 999px;
            font-size: .8rem; font-weight: 600; }
  .granted { background: #064E3B; color: #34D399; }
  .denied  { background: #7F1D1D; color: #FCA5A5; }
  .btn { cursor: pointer; border: none; padding: 6px 16px; border-radius: 6px;
         font-size: .8rem; font-weight: 600; transition: .15s; }
  .btn-grant { background: #059669; color: #fff; }
  .btn-grant:hover { background: #047857; }
  .btn-deny  { background: #DC2626; color: #fff; }
  .btn-deny:hover  { background: #B91C1C; }
  .btn-del   { background: #475569; color: #fff; }
  .btn-del:hover   { background: #334155; }
  .device-id { font-family: monospace; font-size: .8rem; color: #94A3B8; }
  .label-input { background: #1E293B; border: 1px solid #334155; color: #E2E8F0;
                 padding: 4px 8px; border-radius: 4px; width: 140px; font-size: .85rem; }
  .empty { text-align: center; padding: 3rem; color: #475569; }
  .stats { display: flex; gap: 1rem; margin-bottom: 2rem; }
  .stat-card { background: #1E293B; border: 1px solid #334155; border-radius: 8px;
               padding: 1rem 1.5rem; flex: 1; }
  .stat-num { font-size: 1.5rem; font-weight: 700; }
  .stat-label { font-size: .8rem; color: #94A3B8; }
  .refresh-note { color: #475569; font-size: .75rem; margin-top: 1rem; text-align: center; }
</style>
</head>
<body>
<div class="wrap">
  <h1>Access Control Panel</h1>
  <p class="subtitle">Manually grant or deny access to payroll app instances</p>

  <div class="key-box">
    <span>API Key:</span> {{ api_key }}
  </div>

  <div class="stats">
    <div class="stat-card">
      <div class="stat-num" style="color:#34D399">{{ granted_count }}</div>
      <div class="stat-label">Granted</div>
    </div>
    <div class="stat-card">
      <div class="stat-num" style="color:#FCA5A5">{{ denied_count }}</div>
      <div class="stat-label">Denied / Pending</div>
    </div>
    <div class="stat-card">
      <div class="stat-num" style="color:#818CF8">{{ total_count }}</div>
      <div class="stat-label">Total Devices</div>
    </div>
  </div>

  <table>
    <tr><th>Device ID</th><th>Label</th><th>Status</th><th>Last Updated</th><th>Actions</th></tr>
    {% if devices %}
    {% for d in devices %}
    <tr>
      <td class="device-id">{{ d.device_id[:16] }}...</td>
      <td>
        <form method="POST" action="/admin/label" style="display:inline">
          <input type="hidden" name="device_id" value="{{ d.device_id }}">
          <input class="label-input" name="label" value="{{ d.label }}"
                 onchange="this.form.submit()">
        </form>
      </td>
      <td>
        {% if d.granted %}
          <span class="status granted">GRANTED</span>
        {% else %}
          <span class="status denied">DENIED</span>
        {% endif %}
      </td>
      <td style="font-size:.8rem;color:#64748B">{{ d.updated_at }}</td>
      <td>
        {% if d.granted %}
        <form method="POST" action="/admin/toggle" style="display:inline">
          <input type="hidden" name="device_id" value="{{ d.device_id }}">
          <input type="hidden" name="action" value="deny">
          <button class="btn btn-deny" type="submit">Deny</button>
        </form>
        {% else %}
        <form method="POST" action="/admin/toggle" style="display:inline">
          <input type="hidden" name="device_id" value="{{ d.device_id }}">
          <input type="hidden" name="action" value="grant">
          <button class="btn btn-grant" type="submit">Grant</button>
        </form>
        {% endif %}
        <form method="POST" action="/admin/delete" style="display:inline; margin-left:4px;">
          <input type="hidden" name="device_id" value="{{ d.device_id }}">
          <button class="btn btn-del" type="submit"
                  onclick="return confirm('Remove this device?')">Remove</button>
        </form>
      </td>
    </tr>
    {% endfor %}
    {% else %}
    <tr><td colspan="5" class="empty">No devices registered yet. Start the payroll app to see devices appear here.</td></tr>
    {% endif %}
  </table>
  <p class="refresh-note">Refresh this page to see new devices</p>
</div>
</body>
</html>
"""

@app.route("/")
def admin_panel():
    conn = get_db()
    devices = conn.execute("SELECT * FROM devices ORDER BY updated_at DESC").fetchall()
    row = conn.execute("SELECT api_key FROM admin WHERE id = 1").fetchone()
    api_key = row["api_key"] if row else "N/A"
    granted_count = sum(1 for d in devices if d["granted"])
    denied_count = sum(1 for d in devices if not d["granted"])
    conn.close()
    return render_template_string(
        ADMIN_HTML,
        devices=devices,
        api_key=api_key,
        granted_count=granted_count,
        denied_count=denied_count,
        total_count=len(devices),
    )

@app.route("/admin/toggle", methods=["POST"])
def admin_toggle():
    device_id = request.form["device_id"]
    action = request.form["action"]
    conn = get_db()
    conn.execute(
        "UPDATE devices SET granted = ?, updated_at = datetime('now') WHERE device_id = ?",
        (1 if action == "grant" else 0, device_id),
    )
    conn.commit()
    conn.close()
    return '<script>location.href="/"</script>'

@app.route("/admin/label", methods=["POST"])
def admin_label():
    conn = get_db()
    conn.execute(
        "UPDATE devices SET label = ?, updated_at = datetime('now') WHERE device_id = ?",
        (request.form["label"], request.form["device_id"]),
    )
    conn.commit()
    conn.close()
    return '<script>location.href="/"</script>'

@app.route("/admin/delete", methods=["POST"])
def admin_delete():
    conn = get_db()
    conn.execute("DELETE FROM devices WHERE device_id = ?", (request.form["device_id"],))
    conn.commit()
    conn.close()
    return '<script>location.href="/"</script>'


if __name__ == "__main__":
    init_db()
    print("  Admin panel running at: http://localhost:5050")
    print("  Press Ctrl+C to stop.\n")
    app.run(host="0.0.0.0", port=5050, debug=False)
