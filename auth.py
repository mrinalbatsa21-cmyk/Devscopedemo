import hashlib
import hmac
from functools import wraps
from typing import Dict, Optional

from flask import redirect, session, url_for

_USERS = {
    "demo": {
        "username": "demo",
        "full_name": "Demo User",
        "password_hash": "",
        "salt": "devscope",
    }
}


def _hash_password(password: str, salt: str) -> str:
    payload = f"{salt}:{password}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ensure_user_hashes() -> None:
    for user in _USERS.values():
        if not user.get("password_hash"):
            user["password_hash"] = _hash_password("demo123", user["salt"])


_ensure_user_hashes()


def get_user(username: str) -> Optional[Dict[str, str]]:
    return _USERS.get(username.lower())


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    actual_hash = _hash_password(password, salt)
    return hmac.compare_digest(actual_hash, expected_hash)


def authenticate_user(username: str, password: str) -> Optional[Dict[str, str]]:
    username = (username or "").strip().lower()
    password = password or ""
    if not username or len(password) < 6:
        return None
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["salt"], user["password_hash"]):
        return None
    return {"username": user["username"], "full_name": user["full_name"]}


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper
