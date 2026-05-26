import os
import sqlite3
import hashlib
import csv
import io
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from flask import Flask, g, redirect, render_template, request, send_file, url_for, abort, flash, session, Response
from dotenv import load_dotenv

from .labels import render_batch_label, render_service_label, render_custom_label
from .printing import print_png

load_dotenv()

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "5055"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/barprep.sqlite")
APP_BASE_URL = os.getenv("APP_BASE_URL", f"http://localhost:{APP_PORT}").rstrip("/")

SESSION_HOURS = int(os.getenv("SESSION_HOURS", "8"))
MAX_PIN_ATTEMPTS = int(os.getenv("MAX_PIN_ATTEMPTS", "6"))
PIN_LOCKOUT_MINUTES = int(os.getenv("PIN_LOCKOUT_MINUTES", "10"))

ROLES = ["Bartender", "Barback", "Bar Prep", "Manager", "Admin"]

ITEM_CATEGORIES = [
    "Juices",
    "Syrups",
    "Purees",
    "Infusions",
    "Spirits",
    "Garnishes",
    "Batches",
    "Sauces",
    "Prep",
    "Other",
]

STORAGE_OPTIONS = ["Keep Refrigerated", "Shelf Stable"]

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "barprep-dev-change-me")
app.permanent_session_lifetime = timedelta(hours=SESSION_HOURS)


def now_local():
    return datetime.now().replace(microsecond=0)

def now_local_iso():
    return now_local().isoformat(timespec="minutes")


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def db():
    if "db" not in g:
        Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def column_exists(conn, table, column):
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(c[1] == column for c in cols)


def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL DEFAULT 'Prep',
        master_shelf_life_days INTEGER NOT NULL DEFAULT 7,
        in_use_shelf_life_hours INTEGER NOT NULL DEFAULT 24,
        storage TEXT NOT NULL DEFAULT 'Keep refrigerated',
        allergens TEXT NOT NULL DEFAULT '',
        active INTEGER NOT NULL DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_code TEXT NOT NULL UNIQUE,
        item_id INTEGER NOT NULL,
        made_at TEXT NOT NULL,
        made_by_user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL,
        notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(item_id) REFERENCES items(id),
        FOREIGN KEY(made_by_user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS service_instances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_code TEXT NOT NULL UNIQUE,
        batch_id INTEGER NOT NULL,
        bottled_at TEXT NOT NULL,
        bottled_by_user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL,
        notes TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(batch_id) REFERENCES batches(id),
        FOREIGN KEY(bottled_by_user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS login_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip_address TEXT NOT NULL,
        attempted_at TEXT NOT NULL,
        success INTEGER NOT NULL DEFAULT 0
    );
    """)

    if not column_exists(conn, "users", "pin_hash"):
        cur.execute("ALTER TABLE users ADD COLUMN pin_hash TEXT NOT NULL DEFAULT ''")
    if not column_exists(conn, "users", "is_admin"):
        cur.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    if not column_exists(conn, "users", "role"):
        cur.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'Bartender'")
    if not column_exists(conn, "items", "brix_percent"):
        cur.execute("ALTER TABLE items ADD COLUMN brix_percent REAL")
    if not column_exists(conn, "items", "abv_percent"):
        cur.execute("ALTER TABLE items ADD COLUMN abv_percent REAL")
    cur.execute("UPDATE users SET role='Admin' WHERE is_admin=1")

    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        cur.executemany(
            "INSERT INTO users (name, pin_hash, is_admin, role) VALUES (?, ?, ?, ?)",
            [("Sean", hash_pin("1234"), 1, "Admin"), ("Cat", hash_pin("2222"), 0, "Bartender")],
        )
    else:
        cur.execute("UPDATE users SET pin_hash=? WHERE pin_hash=''", (hash_pin("1234"),))

    cur.execute("SELECT COUNT(*) AS c FROM items")
    if cur.fetchone()["c"] == 0:
        cur.executemany(
            """
            INSERT INTO items
            (name, category, master_shelf_life_days, in_use_shelf_life_hours, storage, allergens)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("Passionfruit Puree", "Purees", 7, 24, "Keep refrigerated", ""),
                ("Lime Juice", "Juices", 2, 12, "Keep refrigerated", ""),
                ("Orgeat", "Syrups", 30, 72, "Keep refrigerated", "Almond"),
                ("Simple Syrup", "Syrups", 30, 72, "Keep refrigerated", ""),
            ],
        )

    conn.commit()
    conn.close()


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db().execute("SELECT * FROM users WHERE id=? AND active=1", (uid,)).fetchone()


def has_role(*allowed):
    user = current_user()
    return bool(user and user["role"] in allowed)

def elevated_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not has_role("Bar Prep", "Manager", "Admin"):
            flash("This action requires Bar Prep, Manager, or Admin access.")
            return redirect(url_for("index"))
        return fn(*args, **kwargs)
    return wrapper

def manager_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not has_role("Manager", "Admin"):
            flash("This action requires Manager or Admin access.")
            return redirect(url_for("index"))
        return fn(*args, **kwargs)
    return wrapper

@app.context_processor
def inject_user():
    return {"current_user": current_user(), "brand_name": "BarPrep", "roles": ROLES, "has_role": has_role, "item_categories": ITEM_CATEGORIES, "storage_options": STORAGE_OPTIONS}


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            session["next_url"] = request.url
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def client_ip():
    return (request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For", request.remote_addr)).split(",")[0].strip()

def pin_locked_out(ip):
    since = (now_local() - timedelta(minutes=PIN_LOCKOUT_MINUTES)).isoformat(timespec="minutes")
    row = db().execute(
        "SELECT COUNT(*) AS c FROM login_attempts WHERE ip_address=? AND success=0 AND attempted_at >= ?",
        (ip, since),
    ).fetchone()
    return row["c"] >= MAX_PIN_ATTEMPTS

def record_attempt(ip, success):
    db().execute(
        "INSERT INTO login_attempts (ip_address, attempted_at, success) VALUES (?, ?, ?)",
        (ip, now_local_iso(), 1 if success else 0),
    )
    db().commit()

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("index"))
    if request.method == "POST":
        ip = client_ip()
        pin = request.form.get("pin", "").strip()
        if pin_locked_out(ip):
            flash(f"Too many failed PIN attempts. Try again in {PIN_LOCKOUT_MINUTES} minutes.")
            return render_template("login.html")
        user = db().execute(
            "SELECT * FROM users WHERE active=1 AND pin_hash=?",
            (hash_pin(pin),),
        ).fetchone()
        if user:
            session.permanent = True
            session["user_id"] = user["id"]
            record_attempt(ip, True)
            flash(f"Signed in as {user['name']}")
            return redirect(session.pop("next_url", url_for("index")))
        record_attempt(ip, False)
        flash("Incorrect PIN.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Signed out.")
    return redirect(url_for("login"))


def item_abbreviation(name):
    return "".join(word[0] for word in (name or "").upper().split() if word)

def make_batch_code(item_name: str, made_at: datetime) -> str:
    prefix = "".join([word[0] for word in item_name.upper().split()])[:4]
    date_part = made_at.strftime("%Y%m%d")
    cur = db().execute(
        "SELECT COUNT(*) AS c FROM batches WHERE batch_code LIKE ?",
        (f"{prefix}-{date_part}-%",),
    )
    count = cur.fetchone()["c"] + 1
    suffix = chr(ord("A") + count - 1)
    return f"{prefix}-{date_part}-{suffix}"


def make_service_code(batch_code: str) -> str:
    cur = db().execute(
        "SELECT COUNT(*) AS c FROM service_instances WHERE service_code LIKE ?",
        (f"{batch_code}-S%",),
    )
    count = cur.fetchone()["c"] + 1
    return f"{batch_code}-S{count:02d}"


@app.route("/")
@login_required
def index():
    batches = db().execute(
        """
        SELECT b.*, i.name AS item_name, u.name AS made_by
        FROM batches b
        JOIN items i ON i.id = b.item_id
        JOIN users u ON u.id = b.made_by_user_id
        ORDER BY b.created_at DESC
        LIMIT 10
        """
    ).fetchall()
    services = db().execute(
        """
        SELECT s.*, b.batch_code, i.name AS item_name, u.name AS bottled_by
        FROM service_instances s
        JOIN batches b ON b.id = s.batch_id
        JOIN items i ON i.id = b.item_id
        JOIN users u ON u.id = s.bottled_by_user_id
        ORDER BY s.created_at DESC
        LIMIT 10
        """
    ).fetchall()
    return render_template("index.html", batches=batches, services=services)



@app.route("/bottle-existing")
@login_required
def bottle_existing():
    q = request.args.get("q", "").strip()
    params = []
    where = ""
    if q:
        like = f"%{q}%"
        where = """WHERE lower(b.batch_code) LIKE lower(?) OR lower(i.name) LIKE lower(?) OR lower(i.category) LIKE lower(?)"""
        params = [like, like, like]
    rows = db().execute(
        f"""
        SELECT b.*, i.name AS item_name, i.category, u.name AS made_by
        FROM batches b JOIN items i ON i.id=b.item_id JOIN users u ON u.id=b.made_by_user_id
        {where}
        ORDER BY b.created_at DESC LIMIT 50
        """, params).fetchall()
    if q and len(q) <= 4:
        q_abbr=q.upper()
        ids={r["id"] for r in rows}
        extra=[r for r in db().execute("""
            SELECT b.*, i.name AS item_name, i.category, u.name AS made_by
            FROM batches b JOIN items i ON i.id=b.item_id JOIN users u ON u.id=b.made_by_user_id
            ORDER BY b.created_at DESC LIMIT 100
        """).fetchall() if item_abbreviation(r["item_name"])==q_abbr and r["id"] not in ids]
        rows=list(rows)+extra
    return render_template("bottle_existing.html", batches=rows, q=q)

@app.route("/batch/new", methods=["GET", "POST"])
@login_required
def new_batch():
    users = db().execute("SELECT * FROM users WHERE active=1 ORDER BY name").fetchall()
    items = db().execute("SELECT * FROM items WHERE active=1 ORDER BY category, name").fetchall()

    if request.method == "POST":
        item_id = int(request.form["item_id"])
        user_id = int(request.form["user_id"])
        made_at = parse_dt(request.form["made_at"])
        notes = request.form.get("notes", "")
        item = db().execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
        if not item:
            abort(404)
        expires_at = made_at + timedelta(days=item["master_shelf_life_days"])
        batch_code = make_batch_code(item["name"], made_at)
        created_at = now_local_iso()
        db().execute(
            """
            INSERT INTO batches
            (batch_code, item_id, made_at, made_by_user_id, expires_at, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (batch_code, item_id, made_at.isoformat(timespec="minutes"), user_id, expires_at.isoformat(timespec="minutes"), notes, created_at),
        )
        db().commit()
        flash(f"Created batch {batch_code}")
        return redirect(url_for("batch_detail", code=batch_code))
    return render_template("new_batch.html", users=users, items=items, now=now_local_iso())


@app.route("/b/<code>")
def batch_detail(code):
    batch = db().execute(
        """
        SELECT b.*, i.name AS item_name, i.storage, i.allergens, i.in_use_shelf_life_hours,
               u.name AS made_by
        FROM batches b
        JOIN items i ON i.id = b.item_id
        JOIN users u ON u.id = b.made_by_user_id
        WHERE b.batch_code=?
        """,
        (code,),
    ).fetchone()
    if not batch:
        abort(404)
    services = db().execute(
        """
        SELECT s.*, u.name AS bottled_by
        FROM service_instances s
        JOIN users u ON u.id = s.bottled_by_user_id
        WHERE s.batch_id=?
        ORDER BY s.created_at DESC
        """,
        (batch["id"],),
    ).fetchall()
    return render_template("batch_detail.html", batch=batch, services=services)


@app.route("/batch/<code>/bottle", methods=["GET", "POST"])
@login_required
def bottle_batch(code):
    batch = db().execute(
        """
        SELECT b.*, i.name AS item_name, i.in_use_shelf_life_hours, i.storage, u.name AS made_by
        FROM batches b
        JOIN items i ON i.id = b.item_id
        JOIN users u ON u.id = b.made_by_user_id
        WHERE b.batch_code=?
        """,
        (code,),
    ).fetchone()
    if not batch:
        abort(404)
    users = db().execute("SELECT * FROM users WHERE active=1 ORDER BY name").fetchall()
    if request.method == "POST":
        user_id = int(request.form["user_id"])
        bottled_at = parse_dt(request.form["bottled_at"])
        notes = request.form.get("notes", "")
        parent_expires = parse_dt(batch["expires_at"])
        in_use_expires = bottled_at + timedelta(hours=batch["in_use_shelf_life_hours"])
        expires_at = min(parent_expires, in_use_expires)
        service_code = make_service_code(batch["batch_code"])
        created_at = now_local_iso()
        db().execute(
            """
            INSERT INTO service_instances
            (service_code, batch_id, bottled_at, bottled_by_user_id, expires_at, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (service_code, batch["id"], bottled_at.isoformat(timespec="minutes"), user_id, expires_at.isoformat(timespec="minutes"), notes, created_at),
        )
        db().commit()
        flash(f"Created service bottle {service_code}")
        return redirect(url_for("service_detail", code=service_code))
    return render_template("bottle_batch.html", batch=batch, users=users, now=now_local_iso())


@app.route("/s/<code>")
def service_detail(code):
    service = db().execute(
        """
        SELECT s.*, b.batch_code, b.made_at, b.expires_at AS batch_expires_at,
               i.name AS item_name, i.storage, i.allergens,
               maker.name AS made_by, bottler.name AS bottled_by
        FROM service_instances s
        JOIN batches b ON b.id = s.batch_id
        JOIN items i ON i.id = b.item_id
        JOIN users maker ON maker.id = b.made_by_user_id
        JOIN users bottler ON bottler.id = s.bottled_by_user_id
        WHERE s.service_code=?
        """,
        (code,),
    ).fetchone()
    if not service:
        abort(404)
    return render_template("service_detail.html", service=service)


def load_batch_for_label(code):
    return db().execute(
        """
        SELECT b.*, i.name AS item_name, i.storage, i.allergens, u.name AS made_by
        FROM batches b JOIN items i ON i.id = b.item_id JOIN users u ON u.id = b.made_by_user_id
        WHERE b.batch_code=?
        """,
        (code,),
    ).fetchone()


def load_service_for_label(code):
    return db().execute(
        """
        SELECT s.*, b.batch_code, b.made_at, i.name AS item_name, i.storage, i.allergens,
               maker.name AS made_by, bottler.name AS bottled_by
        FROM service_instances s
        JOIN batches b ON b.id = s.batch_id
        JOIN items i ON i.id = b.item_id
        JOIN users maker ON maker.id = b.made_by_user_id
        JOIN users bottler ON bottler.id = s.bottled_by_user_id
        WHERE s.service_code=?
        """,
        (code,),
    ).fetchone()


@app.route("/label/batch/<code>.png")
def batch_label_png(code):
    batch = load_batch_for_label(code)
    if not batch:
        abort(404)
    img = render_batch_label(batch, f"{APP_BASE_URL}/b/{code}")
    path = Path("/tmp") / f"{code}.png"
    img.save(path)
    return send_file(path, mimetype="image/png")


@app.route("/label/service/<code>.png")
def service_label_png(code):
    service = load_service_for_label(code)
    if not service:
        abort(404)
    img = render_service_label(service, f"{APP_BASE_URL}/s/{code}")
    path = Path("/tmp") / f"{code}.png"
    img.save(path)
    return send_file(path, mimetype="image/png")


@app.post("/print/batch/<code>")
@login_required
def print_batch(code):
    batch = load_batch_for_label(code)
    if not batch:
        abort(404)
    img = render_batch_label(batch, f"{APP_BASE_URL}/b/{code}")
    flash(print_png(img))
    return redirect(url_for("batch_detail", code=code))


@app.post("/print/service/<code>")
@login_required
def print_service(code):
    service = load_service_for_label(code)
    if not service:
        abort(404)
    img = render_service_label(service, f"{APP_BASE_URL}/s/{code}")
    flash(print_png(img))
    return redirect(url_for("service_detail", code=code))





@app.route("/scan/results")
@login_required
def scan_results():
    q=request.args.get("q","").strip()
    batches=[]; services=[]
    if q:
        like=f"%{q}%"
        batches=db().execute("""
            SELECT b.*, i.name AS item_name, i.category, u.name AS made_by
            FROM batches b JOIN items i ON i.id=b.item_id JOIN users u ON u.id=b.made_by_user_id
            WHERE lower(b.batch_code) LIKE lower(?) OR lower(i.name) LIKE lower(?) OR lower(i.category) LIKE lower(?)
            ORDER BY b.created_at DESC LIMIT 50
        """,(like,like,like)).fetchall()
        services=db().execute("""
            SELECT s.*, b.batch_code, i.name AS item_name, i.category, u.name AS bottled_by
            FROM service_instances s JOIN batches b ON b.id=s.batch_id JOIN items i ON i.id=b.item_id JOIN users u ON u.id=s.bottled_by_user_id
            WHERE lower(s.service_code) LIKE lower(?) OR lower(b.batch_code) LIKE lower(?) OR lower(i.name) LIKE lower(?) OR lower(i.category) LIKE lower(?)
            ORDER BY s.created_at DESC LIMIT 50
        """,(like,like,like,like)).fetchall()
        if len(q)<=4:
            ab=q.upper()
            bid={r["id"] for r in batches}
            batches=list(batches)+[r for r in db().execute("""
                SELECT b.*, i.name AS item_name, i.category, u.name AS made_by
                FROM batches b JOIN items i ON i.id=b.item_id JOIN users u ON u.id=b.made_by_user_id
                ORDER BY b.created_at DESC LIMIT 100
            """).fetchall() if item_abbreviation(r["item_name"])==ab and r["id"] not in bid]
            sid={r["id"] for r in services}
            services=list(services)+[r for r in db().execute("""
                SELECT s.*, b.batch_code, i.name AS item_name, i.category, u.name AS bottled_by
                FROM service_instances s JOIN batches b ON b.id=s.batch_id JOIN items i ON i.id=b.item_id JOIN users u ON u.id=s.bottled_by_user_id
                ORDER BY s.created_at DESC LIMIT 100
            """).fetchall() if item_abbreviation(r["item_name"])==ab and r["id"] not in sid]
    return render_template("scan_results.html", q=q, batches=batches, services=services)

@app.route("/scan", methods=["GET", "POST"])
@login_required
def scan_label():
    if request.method == "POST":
        raw = request.form.get("scan_value", "").strip()
        if not raw:
            flash("Enter or scan a label code.")
            return redirect(url_for("scan_label"))
        value = raw.strip()
        if "/b/" in value:
            code = value.split("/b/", 1)[1].split("?", 1)[0].split("#", 1)[0].strip("/")
            return redirect(url_for("batch_detail", code=code))
        if "/s/" in value:
            code = value.split("/s/", 1)[1].split("?", 1)[0].split("#", 1)[0].strip("/")
            return redirect(url_for("service_detail", code=code))
        service = db().execute("SELECT service_code FROM service_instances WHERE lower(service_code)=lower(?)", (value,)).fetchone()
        if service:
            return redirect(url_for("service_detail", code=service["service_code"]))
        batch = db().execute("SELECT batch_code FROM batches WHERE lower(batch_code)=lower(?)", (value,)).fetchone()
        if batch:
            return redirect(url_for("batch_detail", code=batch["batch_code"]))
        return redirect(url_for("scan_results", q=raw))

    recent_batches = db().execute("""
        SELECT b.batch_code, i.name AS item_name
        FROM batches b JOIN items i ON i.id = b.item_id
        ORDER BY b.created_at DESC LIMIT 6
    """).fetchall()
    recent_services = db().execute("""
        SELECT s.service_code, i.name AS item_name
        FROM service_instances s
        JOIN batches b ON b.id = s.batch_id
        JOIN items i ON i.id = b.item_id
        ORDER BY s.created_at DESC LIMIT 6
    """).fetchall()
    return render_template("scan_label.html", recent_batches=recent_batches, recent_services=recent_services)


@app.route("/custom-label", methods=["GET", "POST"])
@login_required
def custom_label():
    if request.method == "POST":
        title = request.form.get("title", "")
        large_text = request.form.get("large_text", "")
        small_text = request.form.get("small_text", "")
        icon = request.form.get("icon", "")
        footer = request.form.get("footer", "")
        action = request.form.get("action", "preview")

        try:
            img = render_custom_label(title, large_text, small_text, icon, footer)
            path = Path("/tmp") / "barprep_custom_label.png"
            img.save(path)
        except Exception as exc:
            flash(f"Custom label render failed: {exc}")
            return render_template("custom_label.html", form=request.form)

        if action == "print":
            flash(print_png(img))
            return render_template("custom_label.html", form=request.form)

        return send_file(path, mimetype="image/png")

    return render_template("custom_label.html", form={})


@app.route("/items")
@login_required
def items():
    rows = db().execute("SELECT * FROM items ORDER BY category, name").fetchall()
    grouped = {}
    for row in rows:
        grouped.setdefault(row["category"], []).append(row)
    return render_template("items.html", grouped=grouped)


@app.route("/items/new", methods=["GET", "POST"])
@login_required
def item_new():
    if request.method == "POST":
        db().execute(
            """
            INSERT INTO items
            (name, category, master_shelf_life_days, in_use_shelf_life_hours, storage, allergens, brix_percent, abv_percent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.form["name"],
                request.form.get("category", "Prep"),
                int(request.form.get("master_shelf_life_days", "7")),
                int(request.form.get("in_use_shelf_life_hours", "24")),
                request.form.get("storage", "Keep Refrigerated"),
                request.form.get("allergens", ""),
                float(request.form["brix_percent"]) if request.form.get("brix_percent") else None,
                float(request.form["abv_percent"]) if request.form.get("abv_percent") else None,
            ),
        )
        db().commit()
        flash("Item added.")
        return redirect(url_for("items"))
    return render_template("item_edit.html", item=None)


@app.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def item_edit(item_id):
    item = db().execute("SELECT * FROM items WHERE id=?", (item_id,)).fetchone()
    if not item:
        abort(404)
    if request.method == "POST":
        db().execute(
            """
            UPDATE items
            SET name=?, category=?, master_shelf_life_days=?, in_use_shelf_life_hours=?,
                storage=?, allergens=?, brix_percent=?, abv_percent=?, active=?
            WHERE id=?
            """,
            (
                request.form["name"],
                request.form.get("category", "Prep"),
                int(request.form.get("master_shelf_life_days", "7")),
                int(request.form.get("in_use_shelf_life_hours", "24")),
                request.form.get("storage", "Keep Refrigerated"),
                request.form.get("allergens", ""),
                float(request.form["brix_percent"]) if request.form.get("brix_percent") else None,
                float(request.form["abv_percent"]) if request.form.get("abv_percent") else None,
                1 if request.form.get("active") == "on" else 0,
                item_id,
            ),
        )
        db().commit()
        flash("Item updated.")
        return redirect(url_for("items"))
    return render_template("item_edit.html", item=item)


@app.get("/items/export.csv")
@login_required
def export_items():
    rows = db().execute(
        """
        SELECT name, category, master_shelf_life_days, in_use_shelf_life_hours,
               storage, allergens, brix_percent, abv_percent, active
        FROM items
        ORDER BY category, name
        """
    ).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["name", "category", "master_shelf_life_days", "in_use_shelf_life_hours", "storage", "allergens", "brix_percent", "abv_percent", "active"])
    for r in rows:
        writer.writerow([r["name"], r["category"], r["master_shelf_life_days"], r["in_use_shelf_life_hours"], r["storage"], r["allergens"], r["brix_percent"], r["abv_percent"], r["active"]])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=barprep_items.csv"})


@app.route("/users")
@login_required
@manager_required
def users():
    users = db().execute("SELECT * FROM users ORDER BY name").fetchall()
    return render_template("users.html", users=users)


@app.post("/users")
@login_required
@manager_required
def add_user():
    pin = request.form.get("pin", "").strip()
    role = request.form.get("role", "Bartender")
    if role not in ROLES:
        role = "Bartender"
    if len(pin) < 4 or not pin.isdigit():
        flash("PIN must be at least 4 digits.")
        return redirect(url_for("users"))
    if db().execute("SELECT id FROM users WHERE pin_hash=?", (hash_pin(pin),)).fetchone():
        flash("PIN already in use. PINs must be unique.")
        return redirect(url_for("users"))
    db().execute("INSERT INTO users (name, pin_hash, is_admin, role) VALUES (?, ?, ?, ?)", (request.form["name"], hash_pin(pin), 1 if role == "Admin" else 0, role))
    db().commit()
    return redirect(url_for("users"))


@app.post("/users/<int:user_id>")
@login_required
@manager_required
def update_user(user_id):
    role = request.form.get("role", "Bartender")
    if role not in ROLES:
        role = "Bartender"
    active = 1 if request.form.get("active") == "on" else 0
    db().execute("UPDATE users SET name=?, role=?, is_admin=?, active=? WHERE id=?", (request.form["name"], role, 1 if role == "Admin" else 0, active, user_id))
    pin = request.form.get("pin", "").strip()
    if pin:
        if len(pin) < 4 or not pin.isdigit():
            flash("PIN must be at least 4 digits.")
            return redirect(url_for("users"))
        if db().execute("SELECT id FROM users WHERE pin_hash=? AND id<>?", (hash_pin(pin), user_id)).fetchone():
            flash("PIN already in use. PINs must be unique.")
            return redirect(url_for("users"))
        db().execute("UPDATE users SET pin_hash=? WHERE id=?", (hash_pin(pin), user_id))
    db().commit()
    flash("User updated.")
    return redirect(url_for("users"))


if __name__ == "__main__":
    init_db()
    app.run(host=APP_HOST, port=APP_PORT, debug=False)
