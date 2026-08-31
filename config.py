import os

from dotenv import load_dotenv

load_dotenv()


def _required_secret():
    secret = os.environ.get("SECRET_KEY", "")
    if secret:
        return secret
    if os.environ.get("VERCEL"):
        raise RuntimeError("SECRET_KEY must be configured in Vercel.")
    return "local-licensing-secret-change-me"


class Config:
    SECRET_KEY = _required_secret()
    SESSION_COOKIE_NAME = "saiko_license_owner"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Strict"
    SESSION_COOKIE_SECURE = os.environ.get(
        "SESSION_COOKIE_SECURE", "true" if os.environ.get("VERCEL") else "false"
    ).lower() == "true"
    PERMANENT_SESSION_LIFETIME = 3600
    SEND_FILE_MAX_AGE_DEFAULT = 86400
