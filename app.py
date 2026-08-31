import json
import os
import secrets
import time
from functools import wraps
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import Flask, current_app, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config


MAX_FAILED_LOGINS = 10
FAILED_LOGIN_WINDOW_SECONDS = 15 * 60
_failed_logins = {}


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        return response

    register_routes(app)
    return app


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="saiko-licence-owner-v2")


def _owner_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="Owner authentication required."), 401
        try:
            payload = _serializer().loads(
                header.removeprefix("Bearer ").strip(),
                max_age=current_app.config["OWNER_TOKEN_MAX_AGE"],
            )
        except SignatureExpired:
            return jsonify(error="Owner session expired. Sign in again."), 401
        except BadSignature:
            return jsonify(error="Invalid owner session. Sign in again."), 401
        if payload.get("owner") is not True:
            return jsonify(error="Invalid owner session."), 401
        return view(*args, **kwargs)

    return wrapped


def _client_key(username):
    ip = request.access_route[0] if request.access_route else request.remote_addr or "unknown"
    return f"{ip[:64]}:{username[:80].lower()}"


def _authenticate(username, password):
    expected_username = os.environ.get("LICENSE_ADMIN_USERNAME", "").strip()
    expected_password = os.environ.get("LICENSE_ADMIN_PASSWORD", "")
    if not expected_username or not expected_password:
        raise RuntimeError("Fixed owner login is not configured.")
    key = _client_key(username)
    cutoff = time.time() - FAILED_LOGIN_WINDOW_SECONDS
    attempts = [stamp for stamp in _failed_logins.get(key, []) if stamp >= cutoff]
    if len(attempts) >= MAX_FAILED_LOGINS:
        raise PermissionError("Too many sign-in attempts. Try again in 15 minutes.")
    valid = secrets.compare_digest(username, expected_username) and secrets.compare_digest(
        password, expected_password
    )
    if valid:
        _failed_logins.pop(key, None)
    else:
        attempts.append(time.time())
        _failed_logins[key] = attempts
    return valid


def _inventory_request(method, payload=None):
    integration_key = os.environ.get("LICENSING_INTEGRATION_KEY", "")
    if not integration_key:
        raise RuntimeError("Inventory integration key is not configured.")
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json", "X-Licensing-Key": integration_key}
    if body is not None:
        headers["Content-Type"] = "application/json"
    target = f'{current_app.config["INVENTORY_API_URL"]}/api/licensing-integration/license'
    outbound = Request(target, data=body, headers=headers, method=method)
    try:
        with urlopen(outbound, timeout=20) as response:
            return json.loads(response.read().decode("utf-8")), response.status
    except HTTPError as exc:
        try:
            data = json.loads(exc.read().decode("utf-8"))
        except ValueError:
            data = {"error": f"Inventory returned error {exc.code}."}
        return data, exc.code
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("Cannot reach the inventory service.") from exc


def register_routes(app):
    @app.get("/")
    def index():
        return jsonify(service="Saiko Licence Service", status="online")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/login")
    def login():
        data = request.get_json(silent=True) or {}
        username = data.get("username", "")
        password = data.get("password", "")
        if not isinstance(username, str) or not isinstance(password, str):
            return jsonify(error="Login ID and password must be text."), 400
        try:
            valid = _authenticate(username[:80].strip(), password[:512])
        except PermissionError as exc:
            return jsonify(error=str(exc)), 429
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 503
        if not valid:
            return jsonify(error="Incorrect owner login ID or password."), 401
        return jsonify(token=_serializer().dumps({"owner": True}))

    @app.get("/api/license")
    @_owner_required
    def read_license():
        try:
            data, status = _inventory_request("GET")
            return jsonify(data), status
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 503

    @app.put("/api/license")
    @_owner_required
    def write_license():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="A JSON request body is required."), 400
        try:
            data, status = _inventory_request("PUT", payload)
            return jsonify(data), status
        except RuntimeError as exc:
            return jsonify(error=str(exc)), 503


app = create_app()
