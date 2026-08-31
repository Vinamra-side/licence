import os
import secrets
from functools import wraps

from flask import Flask, abort, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

import db
from config import Config


MAX_FAILED_LOGINS = 10
FAILED_LOGIN_WINDOW_MINUTES = 15


class LoginRateLimitError(Exception):
    pass


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    app.teardown_appcontext(db.close_connection)

    @app.context_processor
    def inject_csrf_token():
        def csrf_token():
            token = session.get("csrf_token")
            if not token:
                token = secrets.token_urlsafe(32)
                session["csrf_token"] = token
            return token
        return {"csrf_token": csrf_token}

    @app.before_request
    def protect_post_requests():
        if request.method != "POST":
            return None
        expected = session.get("csrf_token", "")
        supplied = request.form.get("csrf_token", "")
        if not expected or not secrets.compare_digest(expected, supplied):
            abort(400, description="Invalid or missing security token. Refresh and try again.")

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'",
        )
        return response

    register_routes(app)
    return app


def owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("owner_authenticated"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def authenticate_owner(username, password, ip_address):
    expected_username = os.environ.get("LICENSE_ADMIN_USERNAME", "").strip()
    expected_password = os.environ.get("LICENSE_ADMIN_PASSWORD", "")
    if not expected_username or not expected_password:
        raise RuntimeError("Fixed owner login credentials are not configured.")

    username = (username or "").strip()
    ip_address = (ip_address or "unknown")[:64]
    attempt_key = f"license-owner:{username}"[:80]
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM login_attempts WHERE attempted_at < now() - interval '1 day'")
        cur.execute(
            """
            SELECT COUNT(*) AS count FROM login_attempts
            WHERE username=%s AND ip_address=%s AND succeeded=false
              AND attempted_at >= now() - (%s * interval '1 minute')
            """,
            (attempt_key, ip_address, FAILED_LOGIN_WINDOW_MINUTES),
        )
        if int(cur.fetchone()["count"]) >= MAX_FAILED_LOGINS:
            raise LoginRateLimitError("Too many sign-in attempts. Try again in 15 minutes.")

        valid = secrets.compare_digest(username, expected_username) and secrets.compare_digest(
            password or "", expected_password
        )
        if not valid:
            cur.execute(
                "INSERT INTO login_attempts (username, ip_address, succeeded) VALUES (%s, %s, false)",
                (attempt_key, ip_address),
            )
            conn.commit()
            return False

        cur.execute("DELETE FROM login_attempts WHERE username=%s AND ip_address=%s", (attempt_key, ip_address))
    conn.commit()
    return True


def get_dashboard():
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM license_status WHERE id=1")
        status = cur.fetchone()
        cur.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM app_users WHERE is_active=true) AS accounts,
              (SELECT COUNT(*) FROM subscribers WHERE is_active=true) AS subscribers
            """
        )
        counts = cur.fetchone()
    accounts = int(counts["accounts"])
    subscribers = int(counts["subscribers"])
    active = accounts + subscribers
    limit = int(status["max_users"])
    return status, {
        "active": active,
        "accounts": accounts,
        "subscribers": subscribers,
        "limit": limit,
        "remaining": max(0, limit - active),
    }


def update_license(is_active, max_users, note):
    note = (note or "").strip() or None
    if note and len(note) > 255:
        raise ValueError("Inactive message must be 255 characters or fewer.")
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM license_status WHERE id=1 FOR UPDATE")
            cur.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM app_users WHERE is_active=true) +
                  (SELECT COUNT(*) FROM subscribers WHERE is_active=true) AS active
                """
            )
            active = int(cur.fetchone()["active"])
            if max_users < active:
                raise ValueError(f"Seat limit cannot be below the {active} active users currently using seats.")
            cur.execute(
                """
                UPDATE license_status
                SET is_active=%s, max_users=%s, note=%s, updated_at=now()
                WHERE id=1
                """,
                (is_active, max_users, note),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def register_routes(app):
    @app.route("/manifest.webmanifest")
    def manifest():
        return send_from_directory(
            app.static_folder,
            "manifest.webmanifest",
            mimetype="application/manifest+json",
        )

    @app.route("/service-worker.js")
    def service_worker():
        response = send_from_directory(
            app.static_folder,
            "service-worker.js",
            mimetype="application/javascript",
        )
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Service-Worker-Allowed"] = "/"
        return response

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("owner_authenticated"):
            return redirect(url_for("control"))
        if request.method == "POST":
            try:
                valid = authenticate_owner(
                    request.form.get("username", ""),
                    request.form.get("password", ""),
                    request.access_route[0] if request.access_route else request.remote_addr,
                )
            except LoginRateLimitError as exc:
                flash(str(exc), "error")
                return render_template("login.html"), 429
            except RuntimeError as exc:
                flash(str(exc), "error")
                return render_template("login.html"), 503
            if valid:
                session.clear()
                session["owner_authenticated"] = True
                session.permanent = True
                return redirect(url_for("control"))
            flash("Incorrect owner login ID or password.", "error")
        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        flash("Owner signed out.", "success")
        return redirect(url_for("login"))

    @app.route("/", methods=["GET", "POST"])
    @owner_required
    def control():
        if request.method == "POST":
            try:
                max_users = int(request.form.get("max_users", ""))
                if max_users < 1:
                    raise ValueError("Seat limit must be a whole number of at least 1.")
                update_license(
                    is_active=request.form.get("is_active") == "on",
                    max_users=max_users,
                    note=request.form.get("note"),
                )
                flash("Licence settings updated immediately.", "success")
            except ValueError as exc:
                flash(str(exc), "error")
            return redirect(url_for("control"))
        status, seats = get_dashboard()
        return render_template("control.html", status=status, seats=seats)


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5002)
