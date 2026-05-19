from flask import Flask, redirect, render_template_string, request, session, url_for

from auth import authenticate_user

app = Flask(__name__)
app.secret_key = "devscope-sample-secret"


@app.get("/")
def home():
    return "DevScope sample app is running"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = authenticate_user(username, password)
        if user:
            session["user"] = user
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
