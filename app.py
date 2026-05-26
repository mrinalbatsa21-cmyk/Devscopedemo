from datetime import datetime, timezone

from flask import Flask, redirect, render_template_string, request, session, url_for

from auth import authenticate_user, login_required
from utils import build_activitywatch_payload, build_dashboard_metrics, format_timestamp

app = Flask(__name__)
app.secret_key = "devscope-sample-secret"


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


if __name__ == "__main__":
    app.run(debug=True)
