from datetime import datetime, timezone

from flask import Flask, redirect, render_template_string, request, session, url_for

from auth import authenticate_user, login_required
from utils import (
    build_activitywatch_payload,
    build_audit_entry,
    build_api_fallback,
    build_dashboard_metrics,
    build_notification,
    build_session_summary,
    format_timestamp,
    normalize_preferences,
)

app = Flask(__name__)
app.secret_key = "devscope-sample-secret"
APP_START = datetime.now(timezone.utc)


@app.get("/")
def home():
    return "DevScope sample app is running"


@app.get("/dashboard")
@login_required
def dashboard():
    user = session.get("user", {})
    metrics = build_dashboard_metrics(session.get("login_at"))
    aw_payload = build_activitywatch_payload(user, metrics)
    return render_template_string(
        """
        <h2>Developer Dashboard</h2>
        <p>Welcome, {{ name }}</p>
        <p>Last login: {{ metrics.last_login }}</p>
        <p>Session minutes: {{ metrics.session_minutes }}</p>
        <p>ActivityWatch queued at: {{ aw_payload.queued_at }}</p>
        <button type="button" onclick="toggleIntel()">View task intelligence</button>
        <div id="task-intel" style="display:none;border:1px solid #ddd;padding:10px;margin-top:10px;">
            <h4>Task intelligence</h4>
            <ul>
                <li>Session minutes: {{ metrics.session_minutes }}</li>
                <li>ActivityWatch queued: {{ aw_payload.queued_at }}</li>
            </ul>
        </div>
        <script>
        function toggleIntel() {
            var panel = document.getElementById('task-intel');
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        }
        </script>
        <a href="{{ url_for('logout') }}">Sign out</a>
        """,
        name=user.get("full_name", user.get("username", "User")),
        metrics=metrics,
        aw_payload=aw_payload,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = authenticate_user(username, password)
        if user:
            session["user"] = user
            session["login_at"] = datetime.now(timezone.utc).isoformat()
            return redirect(url_for("home"))
        return render_template_string("<p>Invalid credentials</p>"), 401

    return render_template_string(
        """
        <h3>Login</h3>
        <form method="post">
            <input name="username" placeholder="Username" required />
            <input name="password" type="password" placeholder="Password" required />
            <button type="submit">Sign in</button>
        </form>
        """
    )


@app.get("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("home"))


@app.post("/activitywatch")
@login_required
def activitywatch_upload():
    user = session.get("user", {})
    metrics = build_dashboard_metrics(session.get("login_at"))
    payload = build_activitywatch_payload(user, metrics)
    return {"status": "queued", "payload": payload}


@app.get("/api/session/summary")
@login_required
def session_summary():
    user = session.get("user", {})
    login_at = session.get("login_at")
    return build_session_summary(user, login_at)


@app.get("/api/notifications")
@login_required
def notifications():
    user = session.get("user", {})
    items = [
        build_notification(user, "Sprint review is scheduled", "info"),
        build_notification(user, "New task assigned", "action"),
    ]
    return {"notifications": items}


@app.get("/api/audit")
@login_required
def audit_log():
    user = session.get("user", {})
    return {"events": [build_audit_entry(user, "view_dashboard")]}


@app.route("/api/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    if request.method == "POST":
        incoming = request.get_json(silent=True) or request.form.to_dict()
        prefs = normalize_preferences(incoming)
        session["prefs"] = prefs
        return {"status": "saved", "preferences": prefs}
    prefs = normalize_preferences(session.get("prefs"))
    return {"preferences": prefs}


@app.get("/api/health")
def health():
    uptime_seconds = int((datetime.now(timezone.utc) - APP_START).total_seconds())
    return {"status": "ok", "uptime_seconds": uptime_seconds, "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/status")
def api_status():
    if request.args.get("fallback") == "1":
        reason = request.args.get("reason") or "forced"
        detail = request.args.get("detail")
        return build_api_fallback("status", reason, detail)
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/fallback/ping")
def fallback_ping():
    return build_api_fallback("ping", "manual")


if __name__ == "__main__":
    app.run(debug=True)
