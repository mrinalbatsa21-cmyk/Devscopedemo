from datetime import datetime, timezone
from typing import Dict, Optional


def format_timestamp(value: Optional[str]) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "—"
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def build_dashboard_metrics(login_at: Optional[str]) -> Dict[str, object]:
    last_login = format_timestamp(login_at)
    session_minutes = 0
    if login_at:
        try:
            dt = datetime.fromisoformat(login_at.replace("Z", "+00:00"))
            delta = datetime.now(timezone.utc) - dt
            session_minutes = max(0, int(delta.total_seconds() / 60))
        except ValueError:
            session_minutes = 0
    return {"last_login": last_login, "session_minutes": session_minutes}


def build_activitywatch_payload(
    user: Dict[str, str],
    metrics: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    username = user.get("username") or "unknown"
    session_minutes = 0
    if metrics and isinstance(metrics.get("session_minutes"), int):
        session_minutes = metrics["session_minutes"]
    return {
        "user": username,
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "session_minutes": session_minutes,
    }


def build_session_summary(user: Dict[str, str], login_at: Optional[str]) -> Dict[str, object]:
    metrics = build_dashboard_metrics(login_at)
    return {
        "user": user.get("username") or "unknown",
        "last_login": metrics["last_login"],
        "session_minutes": metrics["session_minutes"],
    }


def build_api_fallback(service: str, reason: str) -> Dict[str, object]:
    return {
        "status": "fallback",
        "service": service or "unknown",
        "reason": reason or "unknown",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def mask_email(email: str) -> str:
    if "@" not in email:
        return email
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        return f"{name[0]}***@{domain}"
    return f"{name[0]}***{name[-1]}@{domain}"


def safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
