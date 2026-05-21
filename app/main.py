import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from flask import Flask, g, redirect, render_template, request, send_file, url_for, abort, flash
from dotenv import load_dotenv

from .labels import render_batch_label, render_service_label
from .printing import print_png

load_dotenv()

APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "5055"))
DATABASE_PATH = os.getenv("DATABASE_PATH", "/app/data/kitchen_labels.sqlite")
APP_BASE_URL = os.getenv("APP_BASE_URL", f"http://localhost:{APP_PORT}").rstrip("/")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-change-me")


def now_local_iso():
    # Simple local timestamp for MVP. Later we can add timezone config.
    return datetime.now().replace(microsecond=0).isoformat(timespec="minutes")


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


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
    """)

    # Seed users/items.
    cur.execute("SELECT COUNT(*) AS c FROM users")
    if cur.fetchone()["c"] == 0:
        cur.executemany("INSERT INTO users (name) VALUES (?)", [("Sean",), ("Cat",)])

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


@app.route("/batch/new", methods=["GET", "POST"])
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
            (
                batch_code,
                item_id,
                made_at.isoformat(timespec="minutes"),
                user_id,
                expires_at.isoformat(timespec="minutes"),
                notes,
                created_at,
            ),
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
            (
                service_code,
                batch["id"],
                bottled_at.isoformat(timespec="minutes"),
                user_id,
                expires_at.isoformat(timespec="minutes"),
                notes,
                created_at,
            ),
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


@app.route("/label/batch/<code>.png")
def batch_label_png(code):
    batch = db().execute(
        """
        SELECT b.*, i.name AS item_name, i.storage, i.allergens, u.name AS made_by
        FROM batches b
        JOIN items i ON i.id = b.item_id
        JOIN users u ON u.id = b.made_by_user_id
        WHERE b.batch_code=?
        """,
        (code,),
    ).fetchone()
    if not batch:
        abort(404)
    img = render_batch_label(batch, f"{APP_BASE_URL}/b/{code}")
    path = Path("/tmp") / f"{code}.png"
    img.save(path)
    return send_file(path, mimetype="image/png")


@app.route("/label/service/<code>.png")
def service_label_png(code):
    service = db().execute(
        """
        SELECT s.*, b.batch_code, b.made_at,
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
    img = render_service_label(service, f"{APP_BASE_URL}/s/{code}")
    path = Path("/tmp") / f"{code}.png"
    img.save(path)
    return send_file(path, mimetype="image/png")


@app.post("/print/batch/<code>")
def print_batch(code):
    batch = db().execute(
        """
        SELECT b.*, i.name AS item_name, i.storage, i.allergens, u.name AS made_by
        FROM batches b
        JOIN items i ON i.id = b.item_id
        JOIN users u ON u.id = b.made_by_user_id
        WHERE b.batch_code=?
        """,
        (code,),
    ).fetchone()
    if not batch:
        abort(404)
    img = render_batch_label(batch, f"{APP_BASE_URL}/b/{code}")
    result = print_png(img)
    flash(result)
    return redirect(url_for("batch_detail", code=code))


@app.post("/print/service/<code>")
def print_service(code):
    service = db().execute(
        """
        SELECT s.*, b.batch_code, b.made_at,
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
    img = render_service_label(service, f"{APP_BASE_URL}/s/{code}")
    result = print_png(img)
    flash(result)
    return redirect(url_for("service_detail", code=code))


@app.route("/items")
def items():
    items = db().execute("SELECT * FROM items ORDER BY category, name").fetchall()
    users = db().execute("SELECT * FROM users ORDER BY name").fetchall()
    return render_template("items.html", items=items, users=users)


@app.post("/items")
def add_item():
    db().execute(
        """
        INSERT INTO items
        (name, category, master_shelf_life_days, in_use_shelf_life_hours, storage, allergens)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            request.form["name"],
            request.form.get("category", "Prep"),
            int(request.form.get("master_shelf_life_days", "7")),
            int(request.form.get("in_use_shelf_life_hours", "24")),
            request.form.get("storage", "Keep refrigerated"),
            request.form.get("allergens", ""),
        ),
    )
    db().commit()
    return redirect(url_for("items"))


@app.post("/users")
def add_user():
    db().execute("INSERT INTO users (name) VALUES (?)", (request.form["name"],))
    db().commit()
    return redirect(url_for("items"))


if __name__ == "__main__":
    init_db()
    app.run(host=APP_HOST, port=APP_PORT, debug=False)
