#!/usr/bin/env python3
"""
ChatWith - Secure Terminal Chat Platform
Created by [Your Name] | NexCore Technologies
"""

import os
import sys
import json
import time
import uuid
import hashlib
import sqlite3
import datetime
import shutil
import re
import getpass
import threading
import random
import string
from pathlib import Path

# ─────────────────────────────────────────────
#  CONFIGURATION
# ─────────────────────────────────────────────
APP_DIR   = Path.home() / ".chatwith"
DB_PATH   = APP_DIR / "chatwith.db"
EXPORT_DIR = APP_DIR / "exports"

APP_DIR.mkdir(exist_ok=True)
EXPORT_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────
#  TERMINAL COLORS & STYLES
# ─────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    ITALIC  = "\033[3m"
    UNDER   = "\033[4m"
    BLINK   = "\033[5m"

    BLACK   = "\033[30m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"

    BRED    = "\033[91m"
    BGREEN  = "\033[92m"
    BYELLOW = "\033[93m"
    BBLUE   = "\033[94m"
    BMAGENTA= "\033[95m"
    BCYAN   = "\033[96m"
    BWHITE  = "\033[97m"

    BG_BLACK  = "\033[40m"
    BG_BLUE   = "\033[44m"
    BG_CYAN   = "\033[46m"
    BG_GREEN  = "\033[42m"

def cl(text, *styles):
    return "".join(styles) + str(text) + C.RESET

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def term_width():
    return shutil.get_terminal_size((80, 24)).columns

def center(text, width=None):
    w = width or term_width()
    clean = re.sub(r'\033\[[0-9;]*m', '', text)
    pad = max(0, (w - len(clean)) // 2)
    return " " * pad + text

def line(char="─", width=None, color=C.CYAN):
    w = width or term_width()
    return cl(char * w, color)

def dline(width=None, color=C.BBLUE):
    w = width or term_width()
    return cl("═" * w, color)

# ─────────────────────────────────────────────
#  DATABASE SETUP
# ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            unique_id   TEXT    UNIQUE NOT NULL,
            username    TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            display_name TEXT   NOT NULL,
            bio         TEXT    DEFAULT '',
            avatar      TEXT    DEFAULT '',
            status      TEXT    DEFAULT 'Hey, I am using ChatWith!',
            created_at  TEXT    NOT NULL,
            last_seen   TEXT    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS contacts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id    INTEGER NOT NULL,
            contact_id  INTEGER NOT NULL,
            nickname    TEXT    DEFAULT '',
            added_at    TEXT    NOT NULL,
            FOREIGN KEY (owner_id)   REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (contact_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(owner_id, contact_id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id   INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content     TEXT    NOT NULL,
            encrypted   INTEGER DEFAULT 0,
            is_read     INTEGER DEFAULT 0,
            deleted_for_sender   INTEGER DEFAULT 0,
            deleted_for_receiver INTEGER DEFAULT 0,
            sent_at     TEXT    NOT NULL,
            FOREIGN KEY (sender_id)   REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            token       TEXT    NOT NULL,
            created_at  TEXT    NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

# ─────────────────────────────────────────────
#  SECURITY UTILITIES
# ─────────────────────────────────────────────
def hash_password(pw):
    salt = "chatwith_salt_2025"
    return hashlib.sha256((pw + salt).encode()).hexdigest()

def verify_password(pw, hashed):
    return hash_password(pw) == hashed

def generate_unique_id():
    """Generate a unique 8-character alphanumeric ID like CW-A1B2C3D4"""
    chars = string.ascii_uppercase + string.digits
    uid = "CW-" + "".join(random.choices(chars, k=8))
    with get_db() as db:
        while db.execute("SELECT 1 FROM users WHERE unique_id=?", (uid,)).fetchone():
            uid = "CW-" + "".join(random.choices(chars, k=8))
    return uid

def xor_encrypt(text, key="chatwith"):
    """Simple XOR encryption for message privacy"""
    key_bytes = key.encode()
    result = []
    for i, ch in enumerate(text.encode()):
        result.append(ch ^ key_bytes[i % len(key_bytes)])
    return bytes(result).hex()

def xor_decrypt(hex_text, key="chatwith"):
    try:
        data = bytes.fromhex(hex_text)
        key_bytes = key.encode()
        result = []
        for i, b in enumerate(data):
            result.append(b ^ key_bytes[i % len(key_bytes)])
        return bytes(result).decode()
    except Exception:
        return hex_text

def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fmt_time(ts):
    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        today = datetime.datetime.today().date()
        if dt.date() == today:
            return dt.strftime("Today %H:%M")
        elif dt.date() == today - datetime.timedelta(days=1):
            return dt.strftime("Yesterday %H:%M")
        else:
            return dt.strftime("%d %b %H:%M")
    except Exception:
        return ts

# ─────────────────────────────────────────────
#  BANNER
# ─────────────────────────────────────────────
def show_banner(subtitle=None):
    w = term_width()
    print()
    print(dline(w))
    print()

    art = [
        r"  ██████╗██╗  ██╗ █████╗ ████████╗      ██╗    ██╗██╗████████╗██╗  ██╗",
        r" ██╔════╝██║  ██║██╔══██╗╚══██╔══╝      ██║    ██║██║╚══██╔══╝██║  ██║",
        r" ██║     ███████║███████║   ██║         ██║ █╗ ██║██║   ██║   ███████║",
        r" ██║     ██╔══██║██╔══██║   ██║         ██║███╗██║██║   ██║   ██╔══██║",
        r" ╚██████╗██║  ██║██║  ██║   ██║         ╚███╔███╔╝██║   ██║   ██║  ██║",
        r"  ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝          ╚══╝╚══╝ ╚═╝   ╚═╝   ╚═╝  ╚═╝",
    ]

    colors = [C.BBLUE, C.BCYAN, C.BBLUE, C.BCYAN, C.BBLUE, C.CYAN]
    for row, color in zip(art, colors):
        try:
            print(center(cl(row, color, C.BOLD), w))
        except Exception:
            # Fallback for terminals that don't support full unicode
            pass

    # Fallback simple banner if above fails
    try:
        test = art[0]
    except Exception:
        print(center(cl("  C H A T   W I T H  ", C.BBLUE, C.BOLD), w))

    print()
    print(center(cl("◈  Secure · Private · Terminal-First Chat Platform  ◈", C.CYAN), w))
    print()

    if subtitle:
        print(center(cl(f"── {subtitle} ──", C.BYELLOW, C.BOLD), w))
        print()

    print(center(cl("Created by  Mahasanjai  |  ZeroByte Technologies", C.DIM, C.WHITE), w))
    print(center(cl(
        "ZeroByte builds cutting-edge privacy-first communication tools for developers.",
        C.DIM), w))
    print(center(cl(
        "ChatWith is our flagship terminal chat platform — no tracking, no cloud lock-in.",
        C.DIM), w))
    print(center(cl(
        "Your data stays local. Your privacy is guaranteed. Built for Termux & Linux.",
        C.DIM), w))
    print()
    print(dline(w))
    print()

# ─────────────────────────────────────────────
#  INPUT HELPERS
# ─────────────────────────────────────────────
def prompt(label, secret=False, allow_empty=False):
    prefix = cl("  ▸ ", C.BCYAN) + cl(label + ": ", C.WHITE, C.BOLD)
    while True:
        try:
            if secret:
                val = getpass.getpass(prefix)
            else:
                val = input(prefix)
            val = val.strip()
            if val or allow_empty:
                return val
            print(cl("  ✗  This field cannot be empty.", C.BRED))
        except (KeyboardInterrupt, EOFError):
            print()
            return None

def menu(options, title=None, color=C.BCYAN):
    """Display a numbered menu and return the user's choice (1-based int)"""
    if title:
        print(cl(f"\n  {title}", C.BYELLOW, C.BOLD))
        print(cl("  " + "─" * (len(title) + 2), C.DIM))
    for i, opt in enumerate(options, 1):
        icon = opt.get("icon", "○")
        label = opt.get("label", "")
        desc  = opt.get("desc", "")
        line_str = cl(f"  {i}. ", color) + cl(f"{icon}  {label}", C.WHITE, C.BOLD)
        if desc:
            line_str += cl(f"  — {desc}", C.DIM)
        print(line_str)
    print()
    while True:
        try:
            raw = input(cl("  Enter choice: ", C.BCYAN)).strip()
            n = int(raw)
            if 1 <= n <= len(options):
                return n
            print(cl(f"  ✗  Please enter 1–{len(options)}.", C.BRED))
        except (ValueError, TypeError):
            print(cl("  ✗  Invalid input. Enter a number.", C.BRED))
        except (KeyboardInterrupt, EOFError):
            return None

def confirm(msg):
    ans = input(cl(f"  {msg} [y/N]: ", C.BYELLOW)).strip().lower()
    return ans == "y"

def success(msg):
    print(cl(f"\n  ✔  {msg}", C.BGREEN, C.BOLD))

def error(msg):
    print(cl(f"\n  ✗  {msg}", C.BRED, C.BOLD))

def info(msg):
    print(cl(f"\n  ℹ  {msg}", C.BCYAN))

def pause(msg="Press Enter to continue..."):
    input(cl(f"\n  {msg}", C.DIM))

# ─────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────
def auth_create_account():
    clear()
    show_banner("Create New Account")

    print(cl("  Account Registration", C.BBLUE, C.BOLD, C.UNDER))
    print(cl("  Your Unique ID will be auto-generated and is used by others to add you.\n", C.DIM))

    username = prompt("Choose a Username (a-z, 0-9, _)")
    if username is None: return

    # Validate username
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        error("Username must be 3–20 characters: letters, numbers, underscores only.")
        pause(); return

    with get_db() as db:
        if db.execute("SELECT 1 FROM users WHERE username=?", (username.lower(),)).fetchone():
            error("Username already taken. Try another.")
            pause(); return

    display_name = prompt("Display Name (shown in chats)")
    if display_name is None: return

    while True:
        password = prompt("Password (min 6 characters)", secret=True)
        if password is None: return
        if len(password) < 6:
            error("Password must be at least 6 characters."); continue
        confirm_pw = prompt("Confirm Password", secret=True)
        if password != confirm_pw:
            error("Passwords do not match."); continue
        break

    bio = prompt("Short Bio (optional — press Enter to skip)", allow_empty=True)
    if bio is None: bio = ""

    unique_id   = generate_unique_id()
    hashed_pw   = hash_password(password)
    ts          = now_str()

    with get_db() as db:
        db.execute(
            "INSERT INTO users (unique_id, username, password, display_name, bio, created_at, last_seen) "
            "VALUES (?,?,?,?,?,?,?)",
            (unique_id, username.lower(), hashed_pw, display_name, bio, ts, ts)
        )

    print()
    print(dline())
    print(center(cl("🎉  Account Created Successfully!", C.BGREEN, C.BOLD)))
    print()
    print(center(cl(f"Your Unique ID:  {unique_id}", C.BYELLOW, C.BOLD)))
    print(center(cl("Share this ID with friends so they can add you as a contact.", C.DIM)))
    print()
    print(dline())
    pause()

def auth_login():
    clear()
    show_banner("Login")

    username = prompt("Username")
    if username is None: return None

    password = prompt("Password", secret=True)
    if password is None: return None

    with get_db() as db:
        user = db.execute(
            "SELECT * FROM users WHERE username=?", (username.lower(),)
        ).fetchone()

    if not user or not verify_password(password, user["password"]):
        error("Invalid username or password. Login failed.")
        pause()
        return None

    # Update last seen
    with get_db() as db:
        db.execute("UPDATE users SET last_seen=? WHERE id=?", (now_str(), user["id"]))

    success(f"Welcome back, {user['display_name']}!  [ ID: {user['unique_id']} ]")
    time.sleep(1.2)
    return dict(user)

# ─────────────────────────────────────────────
#  MAIN MENU HELPERS
# ─────────────────────────────────────────────
def get_contacts(user_id):
    with get_db() as db:
        return db.execute("""
            SELECT c.id, c.contact_id, c.nickname, c.added_at,
                   u.username, u.display_name, u.unique_id, u.status, u.last_seen
            FROM contacts c
            JOIN users u ON u.id = c.contact_id
            WHERE c.owner_id = ?
            ORDER BY u.display_name
        """, (user_id,)).fetchall()

def unread_count(user_id, sender_id):
    with get_db() as db:
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM messages WHERE sender_id=? AND receiver_id=? AND is_read=0",
            (sender_id, user_id)
        ).fetchone()
    return row["cnt"] if row else 0

def last_message(user_id, other_id):
    with get_db() as db:
        row = db.execute("""
            SELECT content, sent_at, sender_id, encrypted
            FROM messages
            WHERE ((sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?))
              AND deleted_for_sender=0 AND deleted_for_receiver=0
            ORDER BY sent_at DESC LIMIT 1
        """, (user_id, other_id, other_id, user_id)).fetchone()
    return row

def send_message(sender_id, receiver_id, content):
    encrypted_content = xor_encrypt(content)
    with get_db() as db:
        db.execute(
            "INSERT INTO messages (sender_id, receiver_id, content, encrypted, sent_at) VALUES (?,?,?,1,?)",
            (sender_id, receiver_id, encrypted_content, now_str())
        )

def get_chat(user_id, other_id, limit=50):
    with get_db() as db:
        rows = db.execute("""
            SELECT m.*, u.display_name as sender_name
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE ((m.sender_id=? AND m.receiver_id=? AND m.deleted_for_sender=0)
                OR (m.sender_id=? AND m.receiver_id=? AND m.deleted_for_receiver=0))
            ORDER BY m.sent_at DESC LIMIT ?
        """, (user_id, other_id, other_id, user_id, limit)).fetchall()
    rows = list(reversed(rows))
    # Mark as read
    with get_db() as db:
        db.execute(
            "UPDATE messages SET is_read=1 WHERE sender_id=? AND receiver_id=? AND is_read=0",
            (other_id, user_id)
        )
    return rows

# ─────────────────────────────────────────────
#  FEATURE: INDEX (Inbox)
# ─────────────────────────────────────────────
def feature_index(user):
    clear()
    show_banner("Inbox")
    contacts = get_contacts(user["id"])
    if not contacts:
        info("No contacts yet. Add contacts from the main menu.")
        pause(); return

    has_any = False
    items = []
    for c in contacts:
        unread = unread_count(user["id"], c["contact_id"])
        last   = last_message(user["id"], c["contact_id"])
        if last or unread:
            has_any = True
        preview = ""
        if last:
            content = xor_decrypt(last["content"]) if last["encrypted"] else last["content"]
            preview = content[:35] + ("…" if len(content) > 35 else "")
        items.append((c, unread, preview, last))

    if not has_any:
        info("No messages yet. Start a conversation!")
        pause(); return

    # Sort: unread first
    items.sort(key=lambda x: (-x[1], x[3]["sent_at"] if x[3] else ""))

    print(cl("  Recent Conversations", C.BBLUE, C.BOLD, C.UNDER))
    print()
    for idx, (c, unread, preview, last) in enumerate(items, 1):
        name = c["nickname"] if c["nickname"] else c["display_name"]
        ts   = fmt_time(last["sent_at"]) if last else ""
        if unread:
            badge = cl(f" ★ {unread} new ", C.BYELLOW, C.BOLD)
            line_str = cl(f"  {idx}. ", C.BCYAN) + cl(name, C.BWHITE, C.BOLD) + badge
        else:
            line_str = cl(f"  {idx}. ", C.CYAN) + cl(name, C.WHITE)
        if preview:
            line_str += cl(f"\n      {preview}", C.DIM)
        if ts:
            line_str += cl(f"  [{ts}]", C.DIM)
        print(line_str)
        print()

    print(cl("  0. Back", C.DIM))
    print()

    while True:
        try:
            raw = input(cl("  Open conversation #: ", C.BCYAN)).strip()
            if raw == "0": return
            n = int(raw)
            if 1 <= n <= len(items):
                c = items[n-1][0]
                contact_user = {"id": c["contact_id"], "display_name": c["display_name"],
                                "username": c["username"], "unique_id": c["unique_id"]}
                chat_session(user, contact_user)
                return
            error(f"Enter 0–{len(items)}")
        except (ValueError, KeyboardInterrupt):
            return

# ─────────────────────────────────────────────
#  FEATURE: CHAT SESSION
# ─────────────────────────────────────────────
def render_chat(user, contact, messages):
    clear()
    w = term_width()
    name = contact["display_name"]
    uid  = contact["unique_id"]

    print(dline(w))
    print(center(cl(f"  💬  Chat with {name}  [{uid}]", C.BBLUE, C.BOLD), w))
    print(dline(w))
    print()

    if not messages:
        print(center(cl("No messages yet. Say hello! 👋", C.DIM), w))
        print()
    else:
        for msg in messages:
            is_me = msg["sender_id"] == user["id"]
            content = xor_decrypt(msg["content"]) if msg["encrypted"] else msg["content"]
            ts = fmt_time(msg["sent_at"])
            read_mark = cl("✓✓", C.BCYAN) if is_me else ""

            if is_me:
                prefix = cl("  You", C.BGREEN, C.BOLD)
                bubble = cl(f" {content} ", C.WHITE)
                line_str = " " * max(0, w - len(content) - 12) + prefix + cl(" ▸ ", C.DIM) + bubble + cl(f" {ts} {read_mark}", C.DIM)
            else:
                prefix = cl(f"  {name}", C.BCYAN, C.BOLD)
                bubble = cl(f" {content} ", C.WHITE)
                line_str = prefix + cl(" ▸ ", C.DIM) + bubble + cl(f" {ts}", C.DIM)

            print(line_str)

    print()
    print(line("─", w, C.DIM))
    print(cl("  Commands: ", C.DIM) + cl("/back", C.CYAN) + cl(" | ", C.DIM) + cl("/delete", C.CYAN) + cl(" | ", C.DIM) + cl("/refresh", C.CYAN) + cl(" | ", C.DIM) + cl("Type message and Enter", C.DIM))
    print(line("─", w, C.DIM))

def chat_session(user, contact):
    while True:
        messages = get_chat(user["id"], contact["id"])
        render_chat(user, contact, messages)

        try:
            raw = input(cl("  Message: ", C.BWHITE, C.BOLD)).strip()
        except (KeyboardInterrupt, EOFError):
            return

        if not raw:
            continue
        if raw.lower() == "/back":
            return
        if raw.lower() == "/refresh":
            continue
        if raw.lower() == "/delete":
            feature_delete_chat(user, contact)
            return

        send_message(user["id"], contact["id"], raw)

def feature_delete_chat(user, contact):
    if confirm(f"Delete your copy of chat history with {contact['display_name']}? This cannot be undone."):
        with get_db() as db:
            db.execute(
                "UPDATE messages SET deleted_for_sender=1 WHERE sender_id=? AND receiver_id=?",
                (user["id"], contact["id"])
            )
            db.execute(
                "UPDATE messages SET deleted_for_receiver=1 WHERE sender_id=? AND receiver_id=?",
                (contact["id"], user["id"])
            )
        success("Chat history deleted for your account.")
        pause()

# ─────────────────────────────────────────────
#  FEATURE: CHAT TO (Select Contact)
# ─────────────────────────────────────────────
def feature_chat_to(user):
    clear()
    show_banner("Chat To")
    contacts = get_contacts(user["id"])
    if not contacts:
        info("No contacts found. Add contacts first.")
        pause(); return

    print(cl("  Your Contacts", C.BBLUE, C.BOLD, C.UNDER))
    print()
    for i, c in enumerate(contacts, 1):
        name    = c["nickname"] if c["nickname"] else c["display_name"]
        unread  = unread_count(user["id"], c["contact_id"])
        badge   = cl(f" [{unread} unread]", C.BYELLOW) if unread else ""
        status  = cl(f" — {c['status'][:30]}", C.DIM) if c["status"] else ""
        print(cl(f"  {i}. ", C.BCYAN) + cl(name, C.BWHITE, C.BOLD) + badge + status)
        print(cl(f"      @{c['username']}  ·  ID: {c['unique_id']}", C.DIM))
        print()

    print(cl("  0. Back\n", C.DIM))
    while True:
        try:
            raw = input(cl("  Select contact #: ", C.BCYAN)).strip()
            if raw == "0": return
            n = int(raw)
            if 1 <= n <= len(contacts):
                c = contacts[n-1]
                contact_user = {"id": c["contact_id"], "display_name": c["display_name"],
                                "username": c["username"], "unique_id": c["unique_id"]}
                chat_session(user, contact_user)
                return
            error(f"Enter 0–{len(contacts)}")
        except (ValueError, KeyboardInterrupt):
            return

# ─────────────────────────────────────────────
#  FEATURE: ADD CONTACT
# ─────────────────────────────────────────────
def feature_add_contact(user):
    while True:
        clear()
        show_banner("Add Contact")
        print(cl("  Add a new contact using their Unique ID.\n", C.DIM))

        print(cl("  Type 0 to go back to Main Menu.", C.DIM))
        print()
        uid = prompt("Enter contact's Unique ID (e.g. CW-XXXXXXXX)")
        if uid is None: return
        if uid.strip() == "0": return

        uid = uid.strip().upper()
        if not re.match(r'^CW-[A-Z0-9]{8}$', uid):
            error("Invalid format. Unique ID looks like: CW-A1B2C3D4")
            pause(); continue

        if uid == user["unique_id"]:
            error("You cannot add yourself as a contact.")
            pause(); continue

        with get_db() as db:
            found = db.execute("SELECT * FROM users WHERE unique_id=?", (uid,)).fetchone()

        if not found:
            error(f"No user found with ID: {uid}")
            pause(); continue

        with get_db() as db:
            already = db.execute(
                "SELECT 1 FROM contacts WHERE owner_id=? AND contact_id=?",
                (user["id"], found["id"])
            ).fetchone()

        if already:
            info(f"{found['display_name']} is already in your contacts.")
            pause(); return

        print()
        print(cl("  Contact Found:", C.BGREEN, C.BOLD))
        print(cl(f"    Display Name : {found['display_name']}", C.WHITE))
        print(cl(f"    Username     : @{found['username']}", C.WHITE))
        print(cl(f"    Unique ID    : {found['unique_id']}", C.BYELLOW))
        print(cl(f"    Bio          : {found['bio'] or '—'}", C.DIM))
        print()

        print(cl("  1. ✅  Add Contact", C.BGREEN))
        print(cl("  2. 🔄  Search Again", C.BCYAN))
        print(cl("  3. 🔙  Back to Main Menu\n", C.DIM))

        try:
            ch = input(cl("  Choice: ", C.BCYAN)).strip()
        except (KeyboardInterrupt, EOFError):
            return

        if ch == "1":
            nickname = prompt("Set a Nickname (optional — press Enter to skip)", allow_empty=True)
            if nickname is None: nickname = ""
            with get_db() as db:
                db.execute(
                    "INSERT INTO contacts (owner_id, contact_id, nickname, added_at) VALUES (?,?,?,?)",
                    (user["id"], found["id"], nickname, now_str())
                )
            success(f"{found['display_name']} added to your contacts!")
            pause(); return
        elif ch == "2":
            continue
        else:
            return

# ─────────────────────────────────────────────
#  FEATURE: REMOVE CONTACT
# ─────────────────────────────────────────────
def feature_remove_contact(user):
    clear()
    show_banner("Remove Contact")
    contacts = get_contacts(user["id"])
    if not contacts:
        info("No contacts to remove.")
        pause(); return

    print(cl("  Select contact to remove:\n", C.DIM))
    for i, c in enumerate(contacts, 1):
        name = c["nickname"] if c["nickname"] else c["display_name"]
        print(cl(f"  {i}. ", C.BRED) + cl(name, C.WHITE) + cl(f"  @{c['username']}", C.DIM))

    print(cl("\n  0. Cancel\n", C.DIM))
    while True:
        try:
            raw = input(cl("  Select #: ", C.BCYAN)).strip()
            if raw == "0": return
            n = int(raw)
            if 1 <= n <= len(contacts):
                c = contacts[n-1]
                name = c["nickname"] if c["nickname"] else c["display_name"]
                if confirm(f"Remove {name} from contacts? Their messages won't be deleted."):
                    with get_db() as db:
                        db.execute(
                            "DELETE FROM contacts WHERE owner_id=? AND contact_id=?",
                            (user["id"], c["contact_id"])
                        )
                    success(f"{name} removed from contacts.")
                    pause()
                return
            error(f"Enter 0–{len(contacts)}")
        except (ValueError, KeyboardInterrupt):
            return

# ─────────────────────────────────────────────
#  FEATURE: IDENTIFY CONTACT
# ─────────────────────────────────────────────
def feature_identify_contact(user):
    while True:
        clear()
        show_banner("Identify Contact")
        print(cl("  Look up any user by their Unique ID.\n", C.DIM))
        print(cl("  Type 0 to go back to Main Menu.", C.DIM))
        print()

        uid = prompt("Enter Unique ID to identify (e.g. CW-XXXXXXXX)")
        if uid is None: return
        if uid.strip() == "0": return

        uid = uid.strip().upper()

        if not re.match(r'^CW-[A-Z0-9]{8}$', uid):
            error("Invalid format. Unique ID looks like: CW-A1B2C3D4")
            pause(); continue

        with get_db() as db:
            found = db.execute("SELECT * FROM users WHERE unique_id=?", (uid,)).fetchone()

        if not found:
            error(f"No user found with ID: {uid}")
            print()
            print(cl("  1. 🔄  Search Again", C.BCYAN))
            print(cl("  2. 🔙  Back to Main Menu\n", C.DIM))
            try:
                ch = input(cl("  Choice: ", C.BCYAN)).strip()
            except (KeyboardInterrupt, EOFError):
                return
            if ch == "1":
                continue
            else:
                return

        # Check if in contacts
        with get_db() as db:
            in_contacts = db.execute(
                "SELECT nickname FROM contacts WHERE owner_id=? AND contact_id=?",
                (user["id"], found["id"])
            ).fetchone()

        w = term_width()
        print()
        print(dline(w))
        print(center(cl("  User Profile  ", C.BBLUE, C.BOLD), w))
        print(dline(w))
        print()

        fields = [
            ("Display Name", found["display_name"]),
            ("Username",     f"@{found['username']}"),
            ("Unique ID",    found["unique_id"]),
            ("Bio",          found["bio"] or "—"),
            ("Status",       found["status"] or "—"),
            ("Member Since", found["created_at"][:10]),
            ("Last Seen",    fmt_time(found["last_seen"])),
            ("In Contacts",  ("Yes — Nickname: " + in_contacts["nickname"]) if in_contacts else "No"),
        ]

        for label, value in fields:
            print(cl(f"    {label:<14}", C.DIM) + cl(f" :  {value}", C.BWHITE))

        print()
        print(dline(w))
        print()
        print(cl("  1. 🔄  Search Again", C.BCYAN))
        print(cl("  2. 🔙  Back to Main Menu\n", C.DIM))

        try:
            ch = input(cl("  Choice: ", C.BCYAN)).strip()
        except (KeyboardInterrupt, EOFError):
            return

        if ch == "1":
            continue
        else:
            return

# ─────────────────────────────────────────────
#  FEATURE: CHAT HISTORY
# ─────────────────────────────────────────────
def feature_chat_history(user):
    clear()
    show_banner("Chat History")
    contacts = get_contacts(user["id"])
    if not contacts:
        info("No contacts to view history with.")
        pause(); return

    print(cl("  Select contact to view history:\n", C.DIM))
    for i, c in enumerate(contacts, 1):
        name = c["nickname"] if c["nickname"] else c["display_name"]
        print(cl(f"  {i}. ", C.BCYAN) + cl(name, C.WHITE))

    print(cl("\n  0. Back\n", C.DIM))
    while True:
        try:
            raw = input(cl("  Select #: ", C.BCYAN)).strip()
            if raw == "0": return
            n = int(raw)
            if 1 <= n <= len(contacts):
                c = contacts[n-1]
                contact_user = {"id": c["contact_id"], "display_name": c["display_name"],
                                "username": c["username"], "unique_id": c["unique_id"]}
                show_history(user, contact_user)
                return
            error(f"Enter 0–{len(contacts)}")
        except (ValueError, KeyboardInterrupt):
            return

def show_history(user, contact):
    clear()
    w = term_width()
    name = contact["display_name"]
    messages = get_chat(user["id"], contact["id"], limit=200)

    print(dline(w))
    print(center(cl(f"  Chat History — {name}", C.BBLUE, C.BOLD), w))
    print(dline(w))
    print()

    if not messages:
        print(center(cl("No chat history found.", C.DIM), w))
    else:
        for msg in messages:
            is_me = msg["sender_id"] == user["id"]
            content = xor_decrypt(msg["content"]) if msg["encrypted"] else msg["content"]
            ts   = msg["sent_at"]
            who  = cl("You", C.BGREEN) if is_me else cl(name, C.BCYAN)
            print(cl(f"  [{ts}] ", C.DIM) + who + cl(" ▸ ", C.DIM) + cl(content, C.WHITE))

    print()
    print(line("─", w, C.DIM))
    print(cl("  1. Download History    2. Back\n", C.DIM))

    try:
        ch = input(cl("  Choice: ", C.BCYAN)).strip()
    except (KeyboardInterrupt, EOFError):
        return

    if ch == "1":
        export_history(user, contact, messages)
    return

def export_history(user, contact, messages):
    filename = EXPORT_DIR / f"chat_{contact['username']}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    lines = [
        "=" * 60,
        f"  ChatWith — Exported Chat History",
        f"  You: {user['display_name']} ({user['unique_id']})",
        f"  With: {contact['display_name']} ({contact['unique_id']})",
        f"  Exported: {now_str()}",
        "=" * 60,
        ""
    ]
    for msg in messages:
        is_me = msg["sender_id"] == user["id"]
        content = xor_decrypt(msg["content"]) if msg["encrypted"] else msg["content"]
        sender = "You" if is_me else contact["display_name"]
        lines.append(f"[{msg['sent_at']}] {sender}: {content}")

    filename.write_text("\n".join(lines), encoding="utf-8")
    success(f"History exported to:\n    {filename}")
    pause()

# ─────────────────────────────────────────────
#  FEATURE: MY PROFILE
# ─────────────────────────────────────────────
def feature_my_profile(user):
    while True:
        clear()
        show_banner("My Profile")
        w = term_width()

        # Reload user
        with get_db() as db:
            u = db.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
        user.update(dict(u))

        fields = [
            ("Display Name", u["display_name"]),
            ("Username",     f"@{u['username']}"),
            ("Unique ID",    u["unique_id"]),
            ("Bio",          u["bio"] or "—"),
            ("Status",       u["status"]),
            ("Member Since", u["created_at"][:10]),
        ]

        print(dline(w))
        for label, value in fields:
            print(cl(f"    {label:<14}", C.DIM) + cl(f" :  {value}", C.BWHITE))
        print(dline(w))
        print()

        print(cl("  1. Update Display Name    2. Update Bio    3. Update Status    4. Change Password    5. Back\n", C.DIM))
        try:
            ch = input(cl("  Choice: ", C.BCYAN)).strip()
        except (KeyboardInterrupt, EOFError):
            return

        if ch == "1":
            val = prompt("New Display Name")
            if val:
                with get_db() as db:
                    db.execute("UPDATE users SET display_name=? WHERE id=?", (val, user["id"]))
                user["display_name"] = val
                success("Display name updated.")
                time.sleep(0.8)
        elif ch == "2":
            val = prompt("New Bio", allow_empty=True)
            if val is not None:
                with get_db() as db:
                    db.execute("UPDATE users SET bio=? WHERE id=?", (val, user["id"]))
                success("Bio updated.")
                time.sleep(0.8)
        elif ch == "3":
            val = prompt("New Status", allow_empty=True)
            if val is not None:
                with get_db() as db:
                    db.execute("UPDATE users SET status=? WHERE id=?", (val, user["id"]))
                success("Status updated.")
                time.sleep(0.8)
        elif ch == "4":
            old = prompt("Current Password", secret=True)
            if not verify_password(old, user["password"]):
                error("Incorrect current password.")
                pause(); continue
            new_pw = prompt("New Password (min 6 chars)", secret=True)
            if len(new_pw) < 6:
                error("Password too short."); pause(); continue
            conf = prompt("Confirm New Password", secret=True)
            if new_pw != conf:
                error("Passwords do not match."); pause(); continue
            with get_db() as db:
                db.execute("UPDATE users SET password=? WHERE id=?", (hash_password(new_pw), user["id"]))
            user["password"] = hash_password(new_pw)
            success("Password changed successfully.")
            pause()
        elif ch == "5":
            return

# ─────────────────────────────────────────────
#  MAIN INTERFACE (Post Login)
# ─────────────────────────────────────────────
def main_interface(user):
    while True:
        clear()
        show_banner(f"Welcome, {user['display_name']}")

        w = term_width()
        print(center(cl(f"Your ID: {user['unique_id']}  ·  @{user['username']}", C.BYELLOW), w))
        print()

        opts = [
            {"icon": "📬", "label": "Inbox",          "desc": "Recent messages & unread"},
            {"icon": "💬", "label": "Chat To",         "desc": "Open a conversation"},
            {"icon": "➕", "label": "Add Contact",     "desc": "Add by Unique ID"},
            {"icon": "➖", "label": "Remove Contact",  "desc": "Remove from contact list"},
            {"icon": "🔍", "label": "Identify Contact","desc": "Look up a user by ID"},
            {"icon": "📜", "label": "Chat History",    "desc": "View & export past chats"},
            {"icon": "👤", "label": "My Profile",      "desc": "Edit your profile & password"},
            {"icon": "🚪", "label": "Logout",          "desc": "Return to main screen"},
        ]

        ch = menu(opts, "Main Menu")
        if ch is None or ch == 8:
            if confirm("Logout and return to main screen?"):
                return

        actions = {
            1: lambda: feature_index(user),
            2: lambda: feature_chat_to(user),
            3: lambda: feature_add_contact(user),
            4: lambda: feature_remove_contact(user),
            5: lambda: feature_identify_contact(user),
            6: lambda: feature_chat_history(user),
            7: lambda: feature_my_profile(user),
        }
        if ch in actions:
            actions[ch]()

# ─────────────────────────────────────────────
#  LANDING SCREEN
# ─────────────────────────────────────────────
def landing():
    while True:
        clear()
        show_banner()

        opts = [
            {"icon": "🔑", "label": "Login",          "desc": "Sign in to your account"},
            {"icon": "🆕", "label": "Create Account", "desc": "Register a new account"},
            {"icon": "🚪", "label": "Exit",           "desc": "Quit ChatWith"},
        ]

        ch = menu(opts, "Welcome — Choose an Option")
        if ch is None or ch == 3:
            clear()
            print()
            print(center(cl("Thank you for using ChatWith. Stay private. Stay connected.", C.BCYAN, C.BOLD)))
            print(center(cl("— NexCore Technologies —", C.DIM)))
            print()
            sys.exit(0)
        elif ch == 1:
            user = auth_login()
            if user:
                main_interface(user)
        elif ch == 2:
            auth_create_account()

# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
def main():
    # Check Python version
    if sys.version_info < (3, 6):
        print("ChatWith requires Python 3.6 or higher.")
        sys.exit(1)

    # Initialize database
    init_db()

    try:
        landing()
    except KeyboardInterrupt:
        print()
        print(cl("\n  Goodbye! — ChatWith by NexCore Technologies\n", C.DIM))
        sys.exit(0)

if __name__ == "__main__":
    main()
