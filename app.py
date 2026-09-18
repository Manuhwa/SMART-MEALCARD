from __future__ import annotations

import json
import os
import sqlite3
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "mealcard.db"

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "mtc-smart-id-dev-key")
app.config["TEMPLATES_AUTO_RELOAD"] = True

PROGRAMMES = [
    "Diploma in Education (Primary) - Junior Programme",
    "Diploma in Education (Primary) - Early Childhood Development",
    "Diploma in Education (Secondary) - Humanities and Languages",
    "Diploma in Education (Secondary) - Sciences",
]

DEPARTMENTS = [
    "Early Childhood Development",
    "Humanities and Languages",
    "Sciences",
    "Educational Foundations",
    "Theory of Education",
    "Teaching Practice",
    "Practicals",
]

SESSIONS = [
    ("morning", "Morning lectures"),
    ("afternoon", "Afternoon lectures"),
    ("assembly", "Assembly"),
    ("chapel", "Chapel"),
    ("teaching_practice", "Teaching practice"),
]

MEALS = [
    ("breakfast", "Breakfast", "06:30-08:30"),
    ("lunch", "Lunch", "12:00-14:00"),
    ("dinner", "Supper", "17:30-19:30"),
]

HOSTELS = ["Nyerere Hall", "Kaguvi Hall", "Mbuya Nehanda Hall", "Chaminuka Hall"]


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            srn TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            other_names TEXT DEFAULT '',
            gender TEXT NOT NULL,
            date_of_birth TEXT NOT NULL,
            national_id TEXT NOT NULL,
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            programme TEXT NOT NULL,
            specialization TEXT DEFAULT '',
            year_of_study INTEGER NOT NULL,
            intake_year INTEGER NOT NULL,
            department TEXT NOT NULL,
            home_district TEXT DEFAULT '',
            home_address TEXT DEFAULT '',
            next_of_kin TEXT DEFAULT '',
            next_of_kin_phone TEXT DEFAULT '',
            hostel TEXT DEFAULT '',
            room_number TEXT DEFAULT '',
            photo TEXT DEFAULT '',
            meal_cleared INTEGER NOT NULL DEFAULT 1,
            meal_block_reason TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            attend_date TEXT NOT NULL,
            session TEXT NOT NULL,
            course TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            marked_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            UNIQUE (student_id, attend_date, session, course)
        );

        CREATE TABLE IF NOT EXISTS meal_servings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            meal_date TEXT NOT NULL,
            meal_type TEXT NOT NULL,
            served_at TEXT NOT NULL,
            served_by TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            UNIQUE (student_id, meal_date, meal_type)
        );
        """
    )
    db.commit()
    if db.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] == 0:
        seed_data(db)


def seed_data(db: sqlite3.Connection):
    now = datetime.now().isoformat(timespec="seconds")
    staff = [
        ("admin", "admin123", "Mrs. R. Chiweshe", "admin"),
        ("lecturer", "lecturer123", "Mr. P. Nyandoro", "lecturer"),
        ("kitchen", "kitchen123", "Mrs. E. Mabhena", "kitchen"),
    ]
    for username, password, name, role in staff:
        db.execute(
            "INSERT INTO users (username, password_hash, full_name, role, created_at) VALUES (?,?,?,?,?)",
            (username, generate_password_hash(password), name, role, now),
        )

    students = [
        ("MTC/2024/0142", "Tendai", "Moyo", "Tafadzwa", "Male", "2003-04-18", "63-2187452-A-42", "0772123401", "tendai.moyo@student.madziwatc.ac.zw", PROGRAMMES[0], "Literacy & Numeracy", 2, 2024, DEPARTMENTS[0], "Shamva", "Ward 8, Madziwa", "Mrs. S. Moyo", "0773452100", HOSTELS[0], "A12", 1, "", "active"),
        ("MTC/2025/0087", "Chipo", "Nyathi", "Rumbidzai", "Female", "2005-09-02", "08-1944331-B-08", "0783342210", "chipo.nyathi@student.madziwatc.ac.zw", PROGRAMMES[1], "Early Childhood Pedagogy", 1, 2025, DEPARTMENTS[0], "Bindura", "Chiwaridzo, Bindura", "Mr. K. Nyathi", "0778891204", HOSTELS[2], "C04", 0, "Outstanding boarding and meal fees — Term 2", "active"),
        ("MTC/2024/0031", "Tafadzwa", "Chikwanha", "", "Male", "2002-11-27", "75-2033118-C-75", "0712456789", "tafadzwa.chikwanha@student.madziwatc.ac.zw", PROGRAMMES[3], "Mathematics & Physics", 2, 2024, DEPARTMENTS[2], "Mazowe", "Glendale", "Mrs. A. Chikwanha", "0772210987", HOSTELS[1], "B07", 1, "", "active"),
        ("MTC/2023/0198", "Rudo", "Mutasa", "Nyasha", "Female", "2001-06-14", "63-1877204-D-63", "0776567890", "rudo.mutasa@student.madziwatc.ac.zw", PROGRAMMES[2], "English & History and Heritage Studies", 3, 2023, DEPARTMENTS[1], "Harare", "Mbare, Harare", "Mr. T. Mutasa", "0774123009", HOSTELS[2], "C19", 1, "", "active"),
        ("MTC/2025/0055", "Blessing", "Dube", "Nkosana", "Male", "2004-01-09", "08-2211456-E-08", "0789901234", "blessing.dube@student.madziwatc.ac.zw", PROGRAMMES[3], "Agriculture", 1, 2025, DEPARTMENTS[2], "Bulawayo", "Nkulumane, Bulawayo", "Mrs. P. Dube", "0713344556", HOSTELS[0], "A21", 1, "", "active"),
        ("MTC/2024/0110", "Farai", "Ncube", "", "Male", "2003-08-21", "28-1998345-F-28", "0772233445", "farai.ncube@student.madziwatc.ac.zw", PROGRAMMES[0], "Social Studies", 2, 2024, DEPARTMENTS[3], "Gweru", "Mkoba 14, Gweru", "Mr. L. Ncube", "0776677889", HOSTELS[3], "D02", 0, "Disciplinary suspension from dining hall — pending hearing", "active"),
        ("MTC/2023/0076", "Nyasha", "Gumbo", "Tariro", "Female", "2002-03-30", "22-1765432-G-22", "0718899001", "nyasha.gumbo@student.madziwatc.ac.zw", PROGRAMMES[1], "Inclusive ECD Practice", 3, 2023, DEPARTMENTS[0], "Mutare", "Dangamvura, Mutare", "Mrs. M. Gumbo", "0775566778", HOSTELS[2], "C11", 1, "", "active"),
        ("MTC/2025/0201", "Tinashe", "Mhlanga", "", "Male", "2005-12-05", "45-2301987-H-45", "0781122334", "tinashe.mhlanga@student.madziwatc.ac.zw", PROGRAMMES[2], "ChiShona & Geography and Environmental Studies", 1, 2025, DEPARTMENTS[1], "Mount Darwin", "Pfura, Mt Darwin", "Mr. S. Mhlanga", "0779988776", HOSTELS[1], "B15", 1, "", "active"),
        ("MTC/2024/0064", "Precious", "Sibanda", "Nokuthula", "Female", "2003-07-12", "08-2100456-J-08", "0774455667", "precious.sibanda@student.madziwatc.ac.zw", PROGRAMMES[3], "Biology & Chemistry", 2, 2024, DEPARTMENTS[2], "Gwanda", "Jahunda, Gwanda", "Mrs. B. Sibanda", "0712233445", HOSTELS[2], "C08", 1, "", "active"),
        ("MTC/2023/0144", "Kudzai", "Mpofu", "Simbarashe", "Male", "2001-10-03", "63-1654321-K-63", "0786677889", "kudzai.mpofu@student.madziwatc.ac.zw", PROGRAMMES[0], "Mathematics", 3, 2023, DEPARTMENTS[4], "Shamva", "Madziwa Mine", "Mrs. C. Mpofu", "0773344556", HOSTELS[0], "A03", 1, "", "active"),
        ("MTC/2025/0118", "Rutendo", "Chari", "", "Female", "2006-02-19", "63-2401123-L-63", "0717788990", "rutendo.chari@student.madziwatc.ac.zw", PROGRAMMES[1], "Child Development", 1, 2025, DEPARTMENTS[0], "Bindura", "Chipadze, Bindura", "Mr. G. Chari", "0778890012", HOSTELS[2], "C22", 0, "Outstanding meal levy — finance office", "active"),
        ("MTC/2024/0089", "Simbarashe", "Mupfumi", "Tawanda", "Male", "2002-05-25", "75-1987654-M-75", "0775566001", "simba.mupfumi@student.madziwatc.ac.zw", PROGRAMMES[3], "Computer Science & Mathematics", 2, 2024, DEPARTMENTS[2], "Harare", "Highfield, Harare", "Mrs. J. Mupfumi", "0782233445", HOSTELS[3], "D18", 1, "", "active"),
    ]

    for row in students:
        db.execute(
            """
            INSERT INTO students (
                srn, first_name, last_name, other_names, gender, date_of_birth, national_id,
                phone, email, programme, specialization, year_of_study, intake_year, department,
                home_district, home_address, next_of_kin, next_of_kin_phone, hostel, room_number,
                meal_cleared, meal_block_reason, status, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            row + (now,),
        )

    ids = {r["srn"]: r["id"] for r in db.execute("SELECT id, srn FROM students")}
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    for srn, session_name, course in [
        ("MTC/2024/0142", "morning", "Theory of Education"),
        ("MTC/2024/0031", "morning", "Theory of Education"),
        ("MTC/2023/0198", "morning", "Theory of Education"),
        ("MTC/2024/0064", "morning", "Theory of Education"),
        ("MTC/2024/0089", "morning", "Theory of Education"),
        ("MTC/2023/0144", "assembly", "College assembly"),
        ("MTC/2025/0055", "morning", "Educational Psychology"),
        ("MTC/2023/0076", "morning", "Educational Psychology"),
    ]:
        db.execute(
            """
            INSERT OR IGNORE INTO attendance
            (student_id, attend_date, session, course, status, marked_by, created_at)
            VALUES (?,?,?,?,?,?,?)
            """,
            (ids[srn], today, session_name, course, "present", "Mr. P. Nyandoro", now),
        )

    for srn, meal_date, meal_type, when in [
        ("MTC/2024/0142", today, "breakfast", now),
        ("MTC/2024/0031", today, "breakfast", now),
        ("MTC/2023/0198", today, "breakfast", now),
        ("MTC/2024/0064", today, "breakfast", now),
        ("MTC/2023/0144", today, "breakfast", now),
        ("MTC/2024/0089", yesterday, "dinner", now),
        ("MTC/2023/0076", yesterday, "lunch", now),
    ]:
        db.execute(
            """
            INSERT OR IGNORE INTO meal_servings
            (student_id, meal_date, meal_type, served_at, served_by)
            VALUES (?,?,?,?,?)
            """,
            (ids[srn], meal_date, meal_type, when, "Mrs. E. Mabhena"),
        )

    db.commit()


@app.before_request
def ensure_db():
    init_db()


def current_user():
    return session.get("user")


def login_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user:
                return redirect(url_for("login", next=request.path))
            if roles and user["role"] not in roles:
                abort(403)
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def student_dict(row: sqlite3.Row) -> dict:
    data = dict(row)
    data["full_name"] = " ".join(
        p for p in [data["first_name"], data.get("other_names") or "", data["last_name"]] if p
    ).replace("  ", " ")
    data["meal_cleared"] = bool(data["meal_cleared"])
    data["qr_payload"] = f"MTC|{data['srn']}"
    return data


def get_student_by_srn(srn: str):
    srn = normalize_srn(srn)
    row = get_db().execute("SELECT * FROM students WHERE srn = ?", (srn,)).fetchone()
    return student_dict(row) if row else None


def normalize_srn(raw: str) -> str:
    text = (raw or "").strip().upper()
    if text.startswith("MTC|"):
        text = text.split("|", 1)[1]
    text = text.replace(" ", "")
    return text


def parse_srn_input(raw: str) -> str:
    return normalize_srn(raw)


def suggested_meal() -> str:
    hour = datetime.now().hour
    if hour < 11:
        return "breakfast"
    if hour < 16:
        return "lunch"
    return "dinner"  # DB value remains "dinner" for compatibility


def meal_status_for(student_id: int, day: str | None = None) -> dict:
    day = day or date.today().isoformat()
    db = get_db()
    served = {
        r["meal_type"]: r["served_at"]
        for r in db.execute(
            "SELECT meal_type, served_at FROM meal_servings WHERE student_id = ? AND meal_date = ?",
            (student_id, day),
        )
    }
    return {
        meal: {"served": meal in served, "at": served.get(meal)}
        for meal, _label, _hours in MEALS
    }


def next_srn(intake_year: int) -> str:
    db = get_db()
    prefix = f"MTC/{intake_year}/"
    rows = db.execute(
        "SELECT srn FROM students WHERE srn LIKE ?", (prefix + "%",)
    ).fetchall()
    numbers = []
    for row in rows:
        try:
            numbers.append(int(row["srn"].rsplit("/", 1)[1]))
        except (IndexError, ValueError):
            continue
    nxt = (max(numbers) + 1) if numbers else 1
    return f"{prefix}{nxt:04d}"


@app.context_processor
def inject_globals():
    return {
        "user": current_user(),
        "college": {
            "name": "Madziwa Teachers College",
            "short": "MTC",
            "place": "Madziwa, Shamva, Zimbabwe",
            "box": "P.O. Box 140, Shamva",
            "motto": "Developing inclusive, innovative and competent teachers",
            "phone": "+263 772 145 972",
            "email": "principal@madziwatc.ac.zw",
        },
        "programmes": PROGRAMMES,
        "departments": DEPARTMENTS,
        "sessions": SESSIONS,
        "meals": MEALS,
        "hostels": HOSTELS,
        "today": date.today().isoformat(),
        "now": datetime.now(),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(home_for(current_user()))
    error = None
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        db = get_db()
        staff = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if staff and check_password_hash(staff["password_hash"], password):
            session["user"] = {
                "id": staff["id"],
                "username": staff["username"],
                "full_name": staff["full_name"],
                "role": staff["role"],
            }
            return redirect(request.args.get("next") or home_for(session["user"]))

        student = get_student_by_srn(username)
        if student and password == "student123" and student["status"] == "active":
            session["user"] = {
                "id": student["id"],
                "username": student["srn"],
                "full_name": student["full_name"],
                "role": "student",
                "student_id": student["id"],
                "srn": student["srn"],
            }
            return redirect(url_for("student_profile", student_id=student["id"]))
        error = "Incorrect username or password."
    return render_template("login.html", error=error)


def home_for(user: dict) -> str:
    if user["role"] == "kitchen":
        return url_for("meal_hall")
    if user["role"] == "lecturer":
        return url_for("attendance")
    if user["role"] == "student":
        return url_for("student_profile", student_id=user["student_id"])
    return url_for("dashboard")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required()
def dashboard():
    user = current_user()
    if user["role"] == "student":
        return redirect(url_for("student_profile", student_id=user["student_id"]))
    if user["role"] == "kitchen":
        return redirect(url_for("meal_hall"))

    db = get_db()
    today = date.today().isoformat()
    stats = {
        "students": db.execute("SELECT COUNT(*) AS n FROM students WHERE status = 'active'").fetchone()["n"],
        "uncleared": db.execute(
            "SELECT COUNT(*) AS n FROM students WHERE status = 'active' AND meal_cleared = 0"
        ).fetchone()["n"],
        "present": db.execute(
            "SELECT COUNT(DISTINCT student_id) AS n FROM attendance WHERE attend_date = ?",
            (today,),
        ).fetchone()["n"],
        "meals_today": db.execute(
            "SELECT COUNT(*) AS n FROM meal_servings WHERE meal_date = ?", (today,)
        ).fetchone()["n"],
    }
    meal_split = {
        row["meal_type"]: row["n"]
        for row in db.execute(
            "SELECT meal_type, COUNT(*) AS n FROM meal_servings WHERE meal_date = ? GROUP BY meal_type",
            (today,),
        )
    }
    recent_meals = [
        student_dict(r)
        for r in db.execute(
            """
            SELECT s.*, m.meal_type, m.served_at
            FROM meal_servings m
            JOIN students s ON s.id = m.student_id
            WHERE m.meal_date = ?
            ORDER BY m.served_at DESC
            LIMIT 8
            """,
            (today,),
        )
    ]
    recent_attendance = [
        student_dict(r)
        for r in db.execute(
            """
            SELECT s.*, a.session, a.course, a.status, a.created_at
            FROM attendance a
            JOIN students s ON s.id = a.student_id
            WHERE a.attend_date = ?
            ORDER BY a.created_at DESC
            LIMIT 8
            """,
            (today,),
        )
    ]
    blocked = [
        student_dict(r)
        for r in db.execute(
            "SELECT * FROM students WHERE meal_cleared = 0 AND status = 'active' ORDER BY last_name"
        )
    ]
    return render_template(
        "dashboard.html",
        stats=stats,
        meal_split=meal_split,
        recent_meals=recent_meals,
        recent_attendance=recent_attendance,
        blocked=blocked,
        suggested_meal=suggested_meal(),
    )


@app.route("/students")
@login_required("admin", "lecturer")
def students():
    q = (request.args.get("q") or "").strip()
    programme = request.args.get("programme") or ""
    year = request.args.get("year") or ""
    clearance = request.args.get("clearance") or ""
    sql = "SELECT * FROM students WHERE 1=1"
    params: list = []
    if q:
        sql += " AND (srn LIKE ? OR first_name LIKE ? OR last_name LIKE ? OR national_id LIKE ? OR other_names LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like, like, like])
    if programme:
        sql += " AND programme = ?"
        params.append(programme)
    if year:
        sql += " AND year_of_study = ?"
        params.append(year)
    if clearance == "cleared":
        sql += " AND meal_cleared = 1"
    elif clearance == "blocked":
        sql += " AND meal_cleared = 0"
    sql += " ORDER BY intake_year DESC, last_name, first_name"
    rows = [student_dict(r) for r in get_db().execute(sql, params)]
    return render_template("students.html", students=rows, filters={"q": q, "programme": programme, "year": year, "clearance": clearance})


@app.route("/students/new", methods=["GET", "POST"])
@login_required("admin")
def student_new():
    intake = date.today().year
    form = {"srn": next_srn(intake), "intake_year": intake, "year_of_study": 1, "meal_cleared": 1, "status": "active"}
    if request.method == "POST":
        form = request.form.to_dict()
        error = save_student(form)
        if error:
            flash(error, "error")
            return render_template("student_form.html", form=form, mode="new")
        flash("Student registered and Smart ID created.", "ok")
        student = get_student_by_srn(form["srn"])
        return redirect(url_for("student_profile", student_id=student["id"]))
    return render_template("student_form.html", form=form, mode="new")


@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required("admin")
def student_edit(student_id: int):
    row = get_db().execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not row:
        abort(404)
    form = student_dict(row)
    if request.method == "POST":
        form = request.form.to_dict()
        form["id"] = student_id
        error = save_student(form, student_id)
        if error:
            flash(error, "error")
            return render_template("student_form.html", form=form, mode="edit")
        flash("Student record updated.", "ok")
        return redirect(url_for("student_profile", student_id=student_id))
    return render_template("student_form.html", form=form, mode="edit")


def save_student(form: dict, student_id: int | None = None) -> str | None:
    required = ["srn", "first_name", "last_name", "gender", "date_of_birth", "national_id", "programme", "year_of_study", "intake_year", "department"]
    if any(not (form.get(k) or "").strip() for k in required):
        return "Please complete every required field."
    srn = normalize_srn(form["srn"])
    db = get_db()
    existing = db.execute("SELECT id FROM students WHERE srn = ?", (srn,)).fetchone()
    if existing and existing["id"] != student_id:
        return "That SRN is already assigned to another student."
    payload = (
        srn,
        form["first_name"].strip(),
        form["last_name"].strip(),
        (form.get("other_names") or "").strip(),
        form["gender"],
        form["date_of_birth"],
        form["national_id"].strip(),
        (form.get("phone") or "").strip(),
        (form.get("email") or "").strip(),
        form["programme"],
        (form.get("specialization") or "").strip(),
        int(form["year_of_study"]),
        int(form["intake_year"]),
        form["department"],
        (form.get("home_district") or "").strip(),
        (form.get("home_address") or "").strip(),
        (form.get("next_of_kin") or "").strip(),
        (form.get("next_of_kin_phone") or "").strip(),
        (form.get("hostel") or "").strip(),
        (form.get("room_number") or "").strip(),
        form.get("photo") or "",
        1 if form.get("meal_cleared") in ("1", "on", 1, True) else 0,
        (form.get("meal_block_reason") or "").strip(),
        form.get("status") or "active",
    )
    if student_id:
        db.execute(
            """
            UPDATE students SET
                srn=?, first_name=?, last_name=?, other_names=?, gender=?, date_of_birth=?,
                national_id=?, phone=?, email=?, programme=?, specialization=?, year_of_study=?,
                intake_year=?, department=?, home_district=?, home_address=?, next_of_kin=?,
                next_of_kin_phone=?, hostel=?, room_number=?, photo=?, meal_cleared=?,
                meal_block_reason=?, status=?
            WHERE id=?
            """,
            payload + (student_id,),
        )
    else:
        db.execute(
            """
            INSERT INTO students (
                srn, first_name, last_name, other_names, gender, date_of_birth, national_id,
                phone, email, programme, specialization, year_of_study, intake_year, department,
                home_district, home_address, next_of_kin, next_of_kin_phone, hostel, room_number,
                photo, meal_cleared, meal_block_reason, status, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            payload + (datetime.now().isoformat(timespec="seconds"),),
        )
    db.commit()
    return None


@app.route("/students/<int:student_id>")
@login_required()
def student_profile(student_id: int):
    user = current_user()
    if user["role"] == "student" and user.get("student_id") != student_id:
        abort(403)
    if user["role"] == "kitchen":
        abort(403)
    row = get_db().execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    if not row:
        abort(404)
    student = student_dict(row)
    db = get_db()
    attendance = db.execute(
        "SELECT * FROM attendance WHERE student_id = ? ORDER BY attend_date DESC, created_at DESC LIMIT 20",
        (student_id,),
    ).fetchall()
    meals = db.execute(
        "SELECT * FROM meal_servings WHERE student_id = ? ORDER BY meal_date DESC, served_at DESC LIMIT 20",
        (student_id,),
    ).fetchall()
    return render_template(
        "student_profile.html",
        student=student,
        attendance=attendance,
        meal_history=meals,
        today_meals=meal_status_for(student_id),
    )


@app.route("/id-cards")
@login_required("admin", "lecturer", "student")
def id_cards():
    user = current_user()
    db = get_db()
    if user["role"] == "student":
        rows = db.execute("SELECT * FROM students WHERE id = ?", (user["student_id"],)).fetchall()
    else:
        q = (request.args.get("q") or "").strip()
        sql = "SELECT * FROM students WHERE status = 'active'"
        params: list = []
        if q:
            sql += " AND (srn LIKE ? OR first_name LIKE ? OR last_name LIKE ?)"
            like = f"%{q}%"
            params.extend([like, like, like])
        sql += " ORDER BY last_name, first_name"
        rows = db.execute(sql, params).fetchall()
    return render_template("id_cards.html", students=[student_dict(r) for r in rows], q=request.args.get("q", ""))


@app.route("/attendance", methods=["GET"])
@login_required("admin", "lecturer")
def attendance():
    day = request.args.get("date") or date.today().isoformat()
    session_name = request.args.get("session") or "morning"
    course = request.args.get("course") or "Theory of Education"
    programme = request.args.get("programme") or ""
    db = get_db()
    sql = "SELECT * FROM students WHERE status = 'active'"
    params: list = []
    if programme:
        sql += " AND programme = ?"
        params.append(programme)
    sql += " ORDER BY last_name, first_name"
    class_list = []
    marked = {
        r["student_id"]: r
        for r in db.execute(
            "SELECT * FROM attendance WHERE attend_date = ? AND session = ? AND course = ?",
            (day, session_name, course),
        )
    }
    for row in db.execute(sql, params):
        student = student_dict(row)
        record = marked.get(student["id"])
        student["mark"] = dict(record) if record else None
        class_list.append(student)
    present = sum(1 for s in class_list if s["mark"] and s["mark"]["status"] == "present")
    return render_template(
        "attendance.html",
        class_list=class_list,
        filters={"date": day, "session": session_name, "course": course, "programme": programme},
        present=present,
    )


@app.route("/meals")
@login_required("admin", "kitchen")
def meal_hall():
    meal = request.args.get("meal") or suggested_meal()
    if meal not in {m[0] for m in MEALS}:
        meal = "lunch"
    today = date.today().isoformat()
    served = [
        student_dict(r)
        for r in get_db().execute(
            """
            SELECT s.*, m.served_at, m.meal_type
            FROM meal_servings m
            JOIN students s ON s.id = m.student_id
            WHERE m.meal_date = ? AND m.meal_type = ?
            ORDER BY m.served_at DESC
            """,
            (today, meal),
        )
    ]
    return render_template("meal_hall.html", meal=meal, served=served, count=len(served))


@app.route("/meals/clearance", methods=["GET", "POST"])
@login_required("admin")
def meal_clearance():
    db = get_db()
    if request.method == "POST":
        student_id = int(request.form["student_id"])
        cleared = 1 if request.form.get("meal_cleared") == "1" else 0
        reason = (request.form.get("meal_block_reason") or "").strip()
        if cleared:
            reason = ""
        db.execute(
            "UPDATE students SET meal_cleared = ?, meal_block_reason = ? WHERE id = ?",
            (cleared, reason, student_id),
        )
        db.commit()
        flash("Meal clearance updated.", "ok")
        return redirect(url_for("meal_clearance", q=request.form.get("q", "")))
    q = (request.args.get("q") or "").strip()
    sql = "SELECT * FROM students WHERE status = 'active'"
    params: list = []
    if q:
        sql += " AND (srn LIKE ? OR first_name LIKE ? OR last_name LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like])
    sql += " ORDER BY meal_cleared, last_name"
    rows = [student_dict(r) for r in db.execute(sql, params)]
    return render_template("meal_clearance.html", students=rows, q=q)


@app.route("/reports")
@login_required("admin", "lecturer")
def reports():
    db = get_db()
    today = date.today().isoformat()
    week_start = (date.today() - timedelta(days=6)).isoformat()
    attendance_week = db.execute(
        """
        SELECT attend_date, COUNT(DISTINCT student_id) AS n
        FROM attendance
        WHERE attend_date >= ? AND status = 'present'
        GROUP BY attend_date
        ORDER BY attend_date
        """,
        (week_start,),
    ).fetchall()
    meals_week = db.execute(
        """
        SELECT meal_date, meal_type, COUNT(*) AS n
        FROM meal_servings
        WHERE meal_date >= ?
        GROUP BY meal_date, meal_type
        ORDER BY meal_date
        """,
        (week_start,),
    ).fetchall()
    by_programme = db.execute(
        """
        SELECT programme, COUNT(*) AS n,
               SUM(CASE WHEN meal_cleared = 1 THEN 1 ELSE 0 END) AS cleared
        FROM students WHERE status = 'active' GROUP BY programme
        """
    ).fetchall()
    top_absent = db.execute(
        """
        SELECT s.*, 
            (SELECT COUNT(*) FROM attendance a WHERE a.student_id = s.id AND a.attend_date >= ?) AS marks
        FROM students s
        WHERE s.status = 'active'
        ORDER BY marks ASC, s.last_name
        LIMIT 8
        """,
        (week_start,),
    ).fetchall()
    return render_template(
        "reports.html",
        attendance_week=attendance_week,
        meals_week=meals_week,
        by_programme=by_programme,
        top_absent=[student_dict(r) for r in top_absent],
        today=today,
        week_start=week_start,
    )


@app.route("/api/lookup", methods=["POST"])
@login_required()
def api_lookup():
    payload = request.get_json(silent=True) or request.form
    srn = parse_srn_input(payload.get("srn") or payload.get("code") or "")
    if not srn:
        return jsonify({"ok": False, "code": "empty", "message": "Enter or scan a student SRN."}), 400
    student = get_student_by_srn(srn)
    if not student:
        return jsonify({"ok": False, "code": "not_found", "message": f"No student found for {srn}."}), 404
    today = date.today().isoformat()
    meals_today = meal_status_for(student["id"], today)
    marks = [
        dict(r)
        for r in get_db().execute(
            "SELECT session, course, status, created_at FROM attendance WHERE student_id = ? AND attend_date = ?",
            (student["id"], today),
        )
    ]
    return jsonify(
        {
            "ok": True,
            "student": student,
            "meals_today": meals_today,
            "attendance_today": marks,
        }
    )


@app.route("/api/meals/serve", methods=["POST"])
@login_required("admin", "kitchen")
def api_serve_meal():
    payload = request.get_json(silent=True) or {}
    srn = parse_srn_input(payload.get("srn") or "")
    meal_type = payload.get("meal") or suggested_meal()
    if meal_type not in {m[0] for m in MEALS}:
        return jsonify({"ok": False, "code": "bad_meal", "message": "Unknown meal period."}), 400
    student = get_student_by_srn(srn)
    if not student:
        return jsonify({"ok": False, "code": "not_found", "message": f"No student found for {srn}."}), 404
    if student["status"] != "active":
        return jsonify({"ok": False, "code": "inactive", "message": "This Smart ID is not active.", "student": student}), 403
    if not student["meal_cleared"]:
        return jsonify(
            {
                "ok": False,
                "code": "not_cleared",
                "message": student["meal_block_reason"] or "Student is not cleared for meals.",
                "student": student,
            }
        ), 403
    today = date.today().isoformat()
    already = get_db().execute(
        "SELECT served_at FROM meal_servings WHERE student_id = ? AND meal_date = ? AND meal_type = ?",
        (student["id"], today, meal_type),
    ).fetchone()
    if already:
        return jsonify(
            {
                "ok": False,
                "code": "already_served",
                "message": f"Portion already collected for {meal_type} at {already['served_at'][11:16] if len(already['served_at']) >= 16 else already['served_at']}.",
                "student": student,
                "served_at": already["served_at"],
            }
        ), 409
    now = datetime.now().isoformat(timespec="seconds")
    try:
        get_db().execute(
            "INSERT INTO meal_servings (student_id, meal_date, meal_type, served_at, served_by) VALUES (?,?,?,?,?)",
            (student["id"], today, meal_type, now, current_user()["full_name"]),
        )
        get_db().commit()
    except sqlite3.IntegrityError:
        # Race condition: concurrent scan inserted the same meal between our check and insert
        get_db().rollback()
        already = get_db().execute(
            "SELECT served_at FROM meal_servings WHERE student_id = ? AND meal_date = ? AND meal_type = ?",
            (student["id"], today, meal_type),
        ).fetchone()
        return jsonify(
            {
                "ok": False,
                "code": "already_served",
                "message": f"Portion already collected for {meal_type} at {already['served_at'][11:16] if already and len(already['served_at']) >= 16 else 'just now'}.",
                "student": student,
                "served_at": already["served_at"] if already else now,
            }
        ), 409
    return jsonify(
        {
            "ok": True,
            "code": "served",
            "message": f"{student['full_name']} may collect {meal_type}.",
            "student": student,
            "served_at": now,
        }
    )


@app.route("/api/attendance/mark", methods=["POST"])
@login_required("admin", "lecturer")
def api_mark_attendance():
    payload = request.get_json(silent=True) or {}
    srn = parse_srn_input(payload.get("srn") or "")
    day = payload.get("date") or date.today().isoformat()
    session_name = payload.get("session") or "morning"
    course = (payload.get("course") or "").strip() or "General"
    status = payload.get("status") or "present"
    if status not in ("present", "late", "absent"):
        return jsonify({"ok": False, "message": "Invalid attendance status."}), 400
    student = get_student_by_srn(srn)
    if not student:
        return jsonify({"ok": False, "code": "not_found", "message": f"No student found for {srn}."}), 404
    now = datetime.now().isoformat(timespec="seconds")
    get_db().execute(
        """
        INSERT INTO attendance (student_id, attend_date, session, course, status, marked_by, created_at)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(student_id, attend_date, session, course)
        DO UPDATE SET status = excluded.status, marked_by = excluded.marked_by, created_at = excluded.created_at
        """,
        (student["id"], day, session_name, course, status, current_user()["full_name"], now),
    )
    get_db().commit()
    return jsonify({"ok": True, "student": student, "status": status, "message": f"{student['full_name']} marked {status}."})


@app.route("/api/srn/preview")
@login_required("admin")
def api_srn_preview():
    try:
        year = int(request.args.get("year") or date.today().year)
    except ValueError:
        year = date.today().year
    return jsonify({"srn": next_srn(year)})


@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403, title="Restricted", message="Your role cannot open this desk."), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, title="Not found", message="That record or page does not exist."), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
