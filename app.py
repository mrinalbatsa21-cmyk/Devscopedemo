from datetime import datetime, timezone

from flask import Flask, redirect, render_template_string, request, session, url_for

from auth import authenticate_user, login_required
from utils import build_dashboard_metrics, format_timestamp

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
    return render_template_string(
        """
        <h2>Developer Dashboard</h2>
        <p>Welcome, {{ name }}</p>
        <p>Last login: {{ metrics.last_login }}</p>
        <p>Session minutes: {{ metrics.session_minutes }}</p>
        <a href="{{ url_for('logout') }}">Sign out</a>
        """,
        name=user.get("full_name", user.get("username", "User")),
        metrics=metrics,
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


if __name__ == "__main__":
    app.run(debug=True)
