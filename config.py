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
    OWNER_TOKEN_MAX_AGE = int(os.environ.get("OWNER_TOKEN_MAX_AGE", str(30 * 24 * 60 * 60)))
