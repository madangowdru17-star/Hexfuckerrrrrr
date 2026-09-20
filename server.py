#!/usr/bin/env python3
"""HEX-PROTOCOL local test API.

Dependency-free Python 3 server for Termux, desktop testing, or Railway-style hosts.
It logs every request and response as JSON lines in requests.log.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
STORE = ROOT / "keys.json"
REQUEST_LOG = ROOT / "requests.log"
STATIC_KEY = "HEX-PROTOCOL-GGHU"
STATIC_KEY_HOURS = 10
STATIC_KEY_MAX_DEVICES = 1
STORE_LOCK = threading.Lock()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def read_keys() -> dict:
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def write_keys(keys: dict) -> None:
    tmp = STORE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(keys, indent=2), encoding="utf-8")
    tmp.replace(STORE)


def log_event(event: dict) -> None:
    event = {"time": utc_now().isoformat(), **event}
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    with REQUEST_LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
    print(line, flush=True)


def json_body(handler: BaseHTTPRequestHandler) -> tuple[dict, str]:
    length = int(handler.headers.get("Content-Length", "0") or 0)
    raw = handler.rfile.read(min(length, 1024 * 1024)) if length else b""
    text = raw.decode("utf-8", errors="replace")
    if text:
        try:
            value = json.loads(text)
            if isinstance(value, dict):
                return value, text
        except json.JSONDecodeError:
            pass
    values = parse_qs(urlparse(handler.path).query)
    form = {key: value[-1] for key, value in values.items()}
    return form, text


def query_values(handler: BaseHTTPRequestHandler) -> dict:
    values = parse_qs(urlparse(handler.path).query)
    return {key: value[-1] for key, value in values.items()}


def action_for(body: dict, query: dict) -> str:
    return str(body.get("action") or query.get("action") or query.get("api") or "").lower()


def validity(days: int, hours: int) -> str:
    parts = []
    if days:
        parts.append(f"{days} Day" + ("" if days == 1 else "s"))
    if hours:
        parts.append(f"{hours} Hour" + ("" if hours == 1 else "s"))
    return " ".join(parts) if parts else "0 Hours"


def parse_expiry(value: object) -> datetime | None:
    """Parse a custom expiry date in UTC."""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError as exc:
            raise ValueError("expires_at must use YYYY-MM-DD HH:MM:SS or ISO-8601") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def custom_key_name(value: object) -> str:
    """Validate and normalize a caller-supplied key name."""
    key = str(value or "").strip().upper()
    if not key or len(key) > 128 or any(ord(char) < 33 or ord(char) > 126 for char in key):
        raise ValueError("custom_key must be 1-128 printable characters")
    return key


def make_record(days: int, hours: int, max_devices: int) -> dict:
    total_hours = max(1, days * 24 + hours)
    now = utc_now()
    return {
        "created_at": utc_text(now),
        "expires_at": utc_text(now + timedelta(hours=total_hours)),
        "hours": total_hours,
        "days": days,
        "validity": validity(days, hours),
        "max_devices": max_devices,
        "devices": [],
    }


def token(key: str, seconds: int) -> str:
    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")

    now = int(time.time())
    header = b64(json.dumps({"alg": "none", "typ": "JWT"}).encode())
    payload = b64(json.dumps({"sub": key, "tier": "standard", "iat": now, "exp": now + seconds}).encode())
    return f"{header}.{payload}.demo"


def response_for(action: str, body: dict, query: dict) -> tuple[int, dict]:
    if action == "challenge":
        return 200, {"nonce": secrets.token_hex(32)}

    if action in {"create", "generate", "new"}:
        days = max(0, int(body.get("days", query.get("days", 0)) or 0))
        hours = max(0, int(body.get("hours", query.get("hours", 10)) or 0))
        max_devices = max(1, min(10000, int(body.get("max_devices", query.get("max_devices", 1)) or 1)))
        requested_key = body.get("custom_key") or body.get("key") or query.get("custom_key") or query.get("key")
        key = custom_key_name(requested_key) if requested_key else "HEX-CHATS-" + secrets.token_hex(4).upper()
        requested_expiry = body.get("expires_at") or query.get("expires_at")
        expiry = parse_expiry(requested_expiry) if requested_expiry else None
        if expiry is not None:
            remaining_hours = max(1, int((expiry - utc_now()).total_seconds() // 3600))
            record = {
                "created_at": utc_text(utc_now()),
                "expires_at": utc_text(expiry),
                "hours": remaining_hours,
                "days": days,
                "validity": validity(days, remaining_hours if not days else hours),
                "max_devices": max_devices,
                "devices": [],
            }
        else:
            record = make_record(days, hours, max_devices)
        with STORE_LOCK:
            keys = read_keys()
            if key in keys:
                return 409, {"ok": False, "error": "key already exists", "key": key}
            keys[key] = record
            write_keys(keys)
        return 200, {"ok": True, "key": key, "validity": record["validity"], "expires_at": record["expires_at"], "max_devices": max_devices, "hours": record["hours"]}

    if action in {"activate", "validate"}:
        key = str(body.get("key") or body.get("license_key") or query.get("key") or "").strip().upper()
        device = str(body.get("device_id") or body.get("device_pubkey") or query.get("device_id") or "").strip()
        if not device and body.get("fingerprint_inputs") is not None:
            device = body["fingerprint_inputs"] if isinstance(body["fingerprint_inputs"], str) else json.dumps(body["fingerprint_inputs"])
        if not key or not device:
            return 400, {"ok": False, "error": "key and device_id are required"}

        with STORE_LOCK:
            keys = read_keys()
            if key == STATIC_KEY and key not in keys:
                keys[key] = make_record(0, STATIC_KEY_HOURS, STATIC_KEY_MAX_DEVICES)
                write_keys(keys)
            record = keys.get(key)
            if not record:
                return 401, {"ok": False, "error": "invalid key"}
            try:
                expires = datetime.strptime(record["expires_at"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            except (KeyError, ValueError):
                return 401, {"ok": False, "error": "invalid key record"}
            if expires <= utc_now():
                return 401, {"ok": False, "error": "key expired"}
            device_hash = hashlib.sha256(device.encode()).hexdigest()
            devices = list(dict.fromkeys(str(item) for item in record.get("devices", [])))
            if device_hash not in devices and len(devices) >= int(record["max_devices"]):
                return 403, {"ok": False, "error": "device limit reached", "max_devices": record["max_devices"]}
            if device_hash not in devices:
                devices.append(device_hash)
                record["devices"] = devices
                keys[key] = record
                write_keys(keys)

        remaining = max(1, int((expires - utc_now()).total_seconds()))
        access = token(key, remaining)
        return 200, {"ok": True, "key": key, "validity": record["validity"], "expires_at": record["expires_at"], "max_devices": record["max_devices"], "hours": record["hours"], "message": "activated", "access_token": access, "refresh_token": access, "lease": record["expires_at"], "tier": "standard", "config_version": 1}

    return 200, {"ok": True, "api": "HEX-PROTOCOL Python test API", "usage": {"create": "POST or GET ?action=create&custom_key=HEX-CIPHER-3HD67HF8&days=0&hours=10&max_devices=10000", "custom_expiry": "Optional expires_at=YYYY-MM-DD HH:MM:SS or ISO-8601", "challenge": "POST ?api=challenge", "activate": "POST ?api=activate with license_key and device_pubkey"}}


class Handler(BaseHTTPRequestHandler):
    server_version = "HEXProtocolTestAPI/1.0"

    def do_GET(self) -> None:
        self.handle_request()

    def do_POST(self) -> None:
        self.handle_request()

    def handle_request(self) -> None:
        query = query_values(self)
        body, raw_body = json_body(self)
        action = action_for(body, query)
        request_event = {
            "event": "request",
            "method": self.command,
            "path": urlparse(self.path).path,
            "query": query,
            "action": action,
            "headers": {key: value for key, value in self.headers.items()},
            "body": raw_body,
        }
        log_event(request_event)
        try:
            status, payload = response_for(action, body, query)
        except Exception as exc:
            status, payload = 500, {"ok": False, "error": "server error", "detail": str(exc)}
        encoded = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
        log_event({"event": "response", "method": self.command, "path": urlparse(self.path).path, "action": action, "status": status, "body": payload})

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="HEX-PROTOCOL local test API")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "10000")))
    args = parser.parse_args()
    print(f"HEX-PROTOCOL API listening on http://{args.host}:{args.port}")
    print(f"Request log: {REQUEST_LOG}")
    with ThreadingHTTPServer((args.host, args.port), Handler) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
