import os
from datetime import datetime

import pymysql
from flask import Flask, g, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash


app = Flask(__name__)
app.secret_key = os.getenv("APP_SECRET_KEY", "dev-secret-key-change-me")
app.config["JSON_AS_ASCII"] = False

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "app"),
    "password": os.getenv("DB_PASSWORD", "NDibCnFewsxnSBtE"),
    "database": os.getenv("DB_NAME", "app"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
}


def api_response(code=1, msg="", **kwargs):
    payload = {"code": code}
    if msg:
        payload["msg"] = msg
    payload.update(kwargs)
    return jsonify(payload)


def get_db():
    if "db" not in g:
        g.db = pymysql.connect(**DB_CONFIG)
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


app.teardown_appcontext(close_db)


def execute_query(sql, params=None, fetchone=False, fetchall=False, commit=False):
    db = get_db()
    with db.cursor() as cursor:
        cursor.execute(sql, params or ())
        result = None
        if fetchone:
            result = cursor.fetchone()
        elif fetchall:
            result = cursor.fetchall()

    if commit:
        db.commit()

    return result


def require_json():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, api_response(0, "Invalid request body")
    return data, None


def require_login():
    if not session.get("login"):
        return api_response(401, "Please login first")
    return None


def normalize_text(value):
    return (value or "").strip()


def password_matches(stored_password, raw_password):
    if not stored_password:
        return False

    if stored_password.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(stored_password, raw_password)

    # Keeps legacy plaintext passwords working until the table is migrated.
    return stored_password == raw_password


@app.route("/login", methods=["POST"])
def login():
    data, error = require_json()
    if error:
        return error

    username = normalize_text(data.get("username"))
    password = normalize_text(data.get("password"))

    if not username or not password:
        return api_response(0, "Username and password are required")

    user = execute_query(
        "SELECT password FROM admin_users WHERE username=%s",
        (username,),
        fetchone=True,
    )

    if user and password_matches(user["password"], password):
        session["login"] = True
        session["username"] = username
        return api_response(1, "Login success")

    return api_response(0, "Invalid username or password")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return api_response(1, "Logged out")


@app.route("/check", methods=["POST"])
def check():
    try:
        data, error = require_json()
        if error:
            return error

        phone = normalize_text(data.get("phone"))
        account_name = normalize_text(data.get("account_name"))

        if not phone:
            return api_response(0, "Phone is required")

        result = execute_query(
            "SELECT account_name, expire_date, status FROM users_license WHERE phone=%s",
            (phone,),
            fetchone=True,
        )

        if not result:
            return api_response(0, "License not found")

        db_account = normalize_text(result["account_name"])
        expire = result["expire_date"]
        status = result["status"]

        if db_account and account_name and db_account != account_name:
            return api_response(0, "Account name mismatch")

        if status == 0:
            return api_response(0, "Account disabled")

        if expire and datetime.now() > expire:
            return api_response(0, "License expired")

        return api_response(1, "OK")
    except Exception:
        app.logger.exception("check endpoint failed")
        return api_response(0, "Internal server error")


@app.route("/api/list")
def list_users():
    login_error = require_login()
    if login_error:
        return login_error

    data = execute_query(
        "SELECT phone, account_name, expire_date, status FROM users_license ORDER BY expire_date DESC",
        fetchall=True,
    )

    items = []
    for row in data:
        items.append(
            {
                "phone": row["phone"],
                "account_name": row["account_name"],
                "expire_date": row["expire_date"].strftime("%Y-%m-%d %H:%M:%S")
                if row["expire_date"]
                else "",
                "status": row["status"],
            }
        )

    return api_response(1, data=items)


@app.route("/api/add", methods=["POST"])
def add_user():
    login_error = require_login()
    if login_error:
        return login_error

    data, error = require_json()
    if error:
        return error

    phone = normalize_text(data.get("phone"))
    account_name = normalize_text(data.get("account_name"))
    expire_raw = normalize_text(data.get("expire"))

    if not phone or not account_name or not expire_raw:
        return api_response(0, "Phone, account name and expire time are required")

    try:
        expire_date = datetime.fromisoformat(expire_raw)
    except ValueError:
        return api_response(0, "Invalid expire time format")

    exists = execute_query(
        "SELECT phone FROM users_license WHERE phone=%s",
        (phone,),
        fetchone=True,
    )
    if exists:
        return api_response(0, "Phone already exists")

    execute_query(
        "INSERT INTO users_license (phone, account_name, expire_date, status) VALUES (%s, %s, %s, 1)",
        (phone, account_name, expire_date),
        commit=True,
    )

    return api_response(1, "Added successfully")


@app.route("/api/delete", methods=["POST"])
def delete_user():
    login_error = require_login()
    if login_error:
        return login_error

    data, error = require_json()
    if error:
        return error

    phone = normalize_text(data.get("phone"))
    if not phone:
        return api_response(0, "Phone is required")

    execute_query(
        "DELETE FROM users_license WHERE phone=%s",
        (phone,),
        commit=True,
    )
    return api_response(1, "Deleted successfully")


@app.route("/api/delete_batch", methods=["POST"])
def delete_batch():
    login_error = require_login()
    if login_error:
        return login_error

    data, error = require_json()
    if error:
        return error

    phones = data.get("phones", [])
    if not isinstance(phones, list):
        return api_response(0, "Invalid phones format")

    phones = [normalize_text(phone) for phone in phones if normalize_text(phone)]
    if not phones:
        return api_response(0, "Please select records first")

    placeholders = ",".join(["%s"] * len(phones))
    execute_query(
        f"DELETE FROM users_license WHERE phone IN ({placeholders})",
        tuple(phones),
        commit=True,
    )

    return api_response(1, "Batch delete success")


@app.route("/api/toggle", methods=["POST"])
def toggle_user():
    login_error = require_login()
    if login_error:
        return login_error

    data, error = require_json()
    if error:
        return error

    phone = normalize_text(data.get("phone"))
    if not phone:
        return api_response(0, "Phone is required")

    result = execute_query(
        "SELECT status FROM users_license WHERE phone=%s",
        (phone,),
        fetchone=True,
    )
    if not result:
        return api_response(0, "User not found")

    new_status = 0 if result["status"] == 1 else 1
    execute_query(
        "UPDATE users_license SET status=%s WHERE phone=%s",
        (new_status, phone),
        commit=True,
    )

    return api_response(1, "Status updated", status=new_status)


@app.route("/")
def home():
    return send_from_directory("templates", "login.html")


@app.route("/index.html")
def admin():
    if not session.get("login"):
        return send_from_directory("templates", "login.html")
    return send_from_directory("templates", "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6688, debug=False)
