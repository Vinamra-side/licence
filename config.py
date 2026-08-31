import os

from dotenv import load_dotenv


load_dotenv()


def _secret_key():
    value = os.environ.get("SECRET_KEY", "")
    if value:
        return value
    if os.environ.get("VERCEL"):
        raise RuntimeError("SECRET_KEY must be configured in Vercel.")
    return "local-licence-secret-change-me"


class Config:
    SECRET_KEY = _secret_key()
    OWNER_TOKEN_MAX_AGE = int(os.environ.get("OWNER_TOKEN_MAX_AGE", str(30 * 24 * 60 * 60)))
    INVENTORY_API_URL = os.environ.get("INVENTORY_API_URL", "https://saiko-inventory.vercel.app").rstrip("/")
