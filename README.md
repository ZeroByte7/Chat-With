# ChatWith — Terminal Chat Platform
**Created by Praveen | NexCore Technologies**

> Secure · Private · Terminal-First · Works on Termux & Linux

---

## Features

- **Secure Accounts** — SHA-256 password hashing, auto-generated Unique IDs
- **End-to-End Encrypted Messages** — XOR encryption stored in local SQLite DB
- **Contact Management** — Add/remove/identify contacts by Unique ID
- **Inbox with Unread Badges** — ★ star marks unread messages
- **Chat History Export** — Download conversations as `.txt` files
- **Profile Editing** — Change display name, bio, status, password
- **100% Local** — No internet needed, no cloud, no tracking

---

## Installation

### Termux (Android)
```bash
pkg install python git
git clone https://github.com/ZeroByte7/Chat-With.git
cd chatwith
bash install.sh
chatwith

     (or)
python3 chatwith.py
```

### Linux / Kali / Ubuntu
```bash
sudo apt install python3
bash install.sh
chatwith
```

### Manual Run (No Install)
```bash
python3 chat.py
```

---

## How to Use

1. **Create Account** → choose a username + password → get your Unique ID (e.g. `CW-A1B2C3D4`)
2. **Share your Unique ID** with friends
3. **Add Contact** → enter their Unique ID
4. **Chat!**

---

## Menu Overview

| Option | Feature |
|--------|---------|
| 1. Inbox | Recent messages with unread ★ markers |
| 2. Chat To | Select contact and start chatting |
| 3. Add Contact | Add by Unique ID |
| 4. Remove Contact | Remove from list |
| 5. Identify Contact | Look up any user by Unique ID |
| 6. Chat History | View full history + download |
| 7. My Profile | Edit name, bio, status, password |

---

## Data & Privacy

- All data stored locally at `~/.chatwith/chatwith.db`
- Messages XOR-encrypted in database
- No network connections required
- Exported chats saved to `~/.chatwith/exports/`

---

*NexCore Technologies — Building privacy-first tools for developers.*
