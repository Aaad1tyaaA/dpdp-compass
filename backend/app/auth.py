"""Accounts: sign-up, sign-in, cookie sessions, and per-user saved state.

- Passwords are hashed with scrypt and a per-user salt; only the hash is stored.
- A session is a random token in an HttpOnly, SameSite=Lax cookie; the database keeps only its SHA-256.
- Repeated failed sign-ins for one email are throttled.
- /api/me/state stores small JSON values per user, so work follows the account across devices.

    AUTH_REQUIRED=false   let /api/* be used without signing in (tests, local scripts)
    AUTH_DB=path          SQLite file (default storage/accounts.db)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

COOKIE = "compass_session"
SESSION_DAYS = 30
MAX_FAILURES, FAILURE_WINDOW = 5, 15 * 60
MAX_STATE_BYTES, MAX_STATE_KEYS = 1_000_000, 60
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}\.[^@\s]{2,}$")
_KEY = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_lock = threading.Lock()
router = APIRouter(tags=["auth"])


def auth_required() -> bool:
    return os.getenv("AUTH_REQUIRED", "true").lower() != "false"


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        path = Path(os.getenv("AUTH_DB") or Path(__file__).resolve().parents[1] / "storage" / "accounts.db")
        path.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(path, check_same_thread=False)
        _conn.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
                pw_hash BLOB NOT NULL, pw_salt BLOB NOT NULL, created_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL, expires_at REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS user_state (user_id TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, updated_at REAL NOT NULL,
                PRIMARY KEY (user_id, key));
            CREATE TABLE IF NOT EXISTS login_failures (email TEXT NOT NULL, at REAL NOT NULL);
        """)
    return _conn


_conn: sqlite3.Connection | None = None


def ensure_demo_account() -> None:
    """Create the DEMO_EMAIL / DEMO_PASSWORD account if it is missing, so a demo login survives a
    host that wipes its disk on restart (free Hugging Face Spaces)."""
    email, password = os.getenv("DEMO_EMAIL", "").strip().lower(), os.getenv("DEMO_PASSWORD", "")
    if not email or len(password) < 8:
        return
    salt = secrets.token_bytes(16)
    with _db():
        _db().execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?)",
                      (secrets.token_hex(16), email, "Demo User", _hash(password, salt), salt, time.time()))


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _public(row) -> dict:
    return {"id": row[0], "email": row[1], "name": row[2]}


def user_for(request: Request) -> dict | None:
    """The signed-in user for this request, from the session cookie."""
    token = request.cookies.get(COOKIE)
    if not token:
        return None
    with _lock:
        row = _db().execute("SELECT u.id, u.email, u.name FROM sessions s JOIN users u ON u.id = s.user_id "
                            "WHERE s.token_hash = ? AND s.expires_at > ?", (_token_hash(token), time.time())).fetchone()
    return _public(row) if row else None


def require_user(request: Request) -> dict:
    user = getattr(request.state, "user", None) or user_for(request)
    if not user:
        raise HTTPException(401, "sign in to continue")
    return user


def user_id(request: Request) -> str | None:
    user = getattr(request.state, "user", None)
    return user["id"] if user else None


def _start_session(response: Response, request: Request, uid: str) -> None:
    token = secrets.token_urlsafe(32)
    with _lock:
        db = _db()
        db.execute("DELETE FROM sessions WHERE expires_at < ?", (time.time(),))
        db.execute("INSERT INTO sessions VALUES (?, ?, ?)", (_token_hash(token), uid, time.time() + SESSION_DAYS * 86400))
        db.commit()
    secure = os.getenv("ENV", "").lower() == "production" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 86400, httponly=True, samesite="lax", secure=secure, path="/")


class SignUp(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=200)
    name: str = Field(default="", max_length=80)


class SignIn(BaseModel):
    email: str = Field(max_length=254)
    password: str = Field(max_length=200)


class Profile(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=200)
    new_password: str = Field(min_length=8, max_length=200)


class Confirm(BaseModel):
    password: str = Field(max_length=200)


class StateValue(BaseModel):
    value: object = None


def _email(raw: str) -> str:
    email = raw.strip().lower()
    if not _EMAIL.match(email):
        raise HTTPException(422, "enter a valid email address")
    return email


@router.post("/api/auth/signup")
def signup(body: SignUp, request: Request, response: Response) -> dict:
    email, salt, uid = _email(body.email), secrets.token_bytes(16), uuid.uuid4().hex
    name = body.name.strip() or email.split("@")[0]
    try:
        with _lock:
            _db().execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)", (uid, email, name, _hash(body.password, salt), salt, time.time()))
            _db().commit()
    except sqlite3.IntegrityError:
        raise HTTPException(409, "an account with this email already exists")
    _start_session(response, request, uid)
    return {"id": uid, "email": email, "name": name}


def _check_password(email: str, password: str) -> tuple | None:
    """The user row if the password is right. Takes the same time whether or not the account exists."""
    with _lock:
        row = _db().execute("SELECT id, email, name, pw_hash, pw_salt FROM users WHERE email = ?", (email,)).fetchone()
    digest = _hash(password, row[4] if row else b"0" * 16)
    return row if row and hmac.compare_digest(digest, row[3]) else None


@router.post("/api/auth/login")
def login(body: SignIn, request: Request, response: Response) -> dict:
    email, now = body.email.strip().lower(), time.time()
    with _lock:
        db = _db()
        db.execute("DELETE FROM login_failures WHERE at < ?", (now - FAILURE_WINDOW,))
        failures = db.execute("SELECT COUNT(*) FROM login_failures WHERE email = ?", (email,)).fetchone()[0]
        db.commit()
    if failures >= MAX_FAILURES:
        raise HTTPException(429, "too many failed attempts; try again in 15 minutes")
    row = _check_password(email, body.password)
    if not row:
        with _lock:
            _db().execute("INSERT INTO login_failures VALUES (?, ?)", (email, now))
            _db().commit()
        raise HTTPException(401, "email or password is incorrect")  # same message for both, so accounts cannot be probed
    with _lock:
        _db().execute("DELETE FROM login_failures WHERE email = ?", (email,))
        _db().commit()
    _start_session(response, request, row[0])
    return _public(row)


@router.post("/api/auth/logout")
def logout(request: Request, response: Response) -> dict:
    token = request.cookies.get(COOKIE)
    if token:
        with _lock:
            _db().execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
            _db().commit()
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@router.get("/api/auth/me")
def me(request: Request) -> dict:
    return {"user": user_for(request), "auth_required": auth_required()}


@router.patch("/api/auth/me")
def update_profile(body: Profile, request: Request) -> dict:
    user = require_user(request)
    with _lock:
        _db().execute("UPDATE users SET name = ? WHERE id = ?", (body.name.strip(), user["id"]))
        _db().commit()
    return {**user, "name": body.name.strip()}


@router.post("/api/auth/password")
def change_password(body: PasswordChange, request: Request, response: Response) -> dict:
    user = require_user(request)
    if not _check_password(user["email"], body.current_password):
        raise HTTPException(401, "current password is incorrect")
    salt = secrets.token_bytes(16)
    with _lock:
        db = _db()
        db.execute("UPDATE users SET pw_hash = ?, pw_salt = ? WHERE id = ?", (_hash(body.new_password, salt), salt, user["id"]))
        db.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))  # sign out everywhere, then start a fresh session here
        db.commit()
    _start_session(response, request, user["id"])
    return {"ok": True}


@router.post("/api/auth/delete")
def delete_account(body: Confirm, request: Request, response: Response) -> dict:
    """Delete the account and everything saved under it."""
    user = require_user(request)
    if not _check_password(user["email"], body.password):
        raise HTTPException(401, "password is incorrect")
    with _lock:
        db = _db()
        for table in ("sessions", "user_state"):
            db.execute(f"DELETE FROM {table} WHERE user_id = ?", (user["id"],))
        db.execute("DELETE FROM users WHERE id = ?", (user["id"],))
        db.commit()
    from app.api.compliance import ANALYSES
    ANALYSES.delete_user(user["id"])
    from app.api.policies import DOCUMENTS
    DOCUMENTS.delete_user(user["id"])
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


# ── saved state ──────────────────────────────────────────────────────────────
@router.get("/api/me/state")
def get_state(request: Request) -> dict:
    user = require_user(request)
    with _lock:
        rows = _db().execute("SELECT key, value FROM user_state WHERE user_id = ?", (user["id"],)).fetchall()
    return {k: json.loads(v) for k, v in rows}


@router.put("/api/me/state/{key}")
def put_state(key: str, body: StateValue, request: Request) -> dict:
    user = require_user(request)
    if not _KEY.match(key):
        raise HTTPException(422, "invalid key")
    raw = json.dumps(body.value, ensure_ascii=False)
    if len(raw.encode()) > MAX_STATE_BYTES:
        raise HTTPException(413, "value too large to save")
    with _lock:
        db = _db()
        known = db.execute("SELECT COUNT(*), SUM(key = ?) FROM user_state WHERE user_id = ?", (key, user["id"])).fetchone()
        if known[0] >= MAX_STATE_KEYS and not known[1]:
            raise HTTPException(409, "too many saved items")
        db.execute("INSERT INTO user_state VALUES (?, ?, ?, ?) ON CONFLICT(user_id, key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                   (user["id"], key, raw, time.time()))
        db.commit()
    return {"ok": True}


@router.delete("/api/me/state")
def clear_state(request: Request) -> dict:
    user = require_user(request)
    with _lock:
        _db().execute("DELETE FROM user_state WHERE user_id = ?", (user["id"],))
        _db().commit()
    return {"ok": True}
