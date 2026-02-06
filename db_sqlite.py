import sqlite3
from pathlib import Path
from uuid import uuid4
import shutil
from datetime import datetime

DB_PATH = Path("gym.db")
EXERCISE_IMG_DIR = Path("assets/exercises")
EXERCISE_IMG_DIR.mkdir(parents=True, exist_ok=True)

def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS routines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS exercises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        routine_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        order_index INTEGER NOT NULL DEFAULT 0,
        default_sets INTEGER NOT NULL DEFAULT 3,
        default_rest_seconds INTEGER NOT NULL DEFAULT 60,
        FOREIGN KEY (routine_id) REFERENCES routines(id) ON DELETE CASCADE
    )
    """)

     # --- Migration: add image_path column if missing ---
    cols = [row["name"] for row in cur.execute("PRAGMA table_info(exercises)").fetchall()]
    if "image_path" not in cols:
        cur.execute("ALTER TABLE exercises ADD COLUMN image_path TEXT")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS workout_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        routine_id INTEGER NOT NULL,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        FOREIGN KEY (routine_id) REFERENCES routines(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS set_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL,
        exercise_id INTEGER NOT NULL,
        set_index INTEGER NOT NULL,
        reps INTEGER NOT NULL,
        weight REAL NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES workout_sessions(id) ON DELETE CASCADE,
        FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

def now_iso():
    return datetime.utcnow().isoformat(timespec="seconds")

# --- Routines ---
def list_routines():
    conn = connect()
    rows = conn.execute("SELECT id, name, created_at FROM routines ORDER BY id DESC").fetchall()
    conn.close()
    return rows

def create_routine(name: str):
    conn = connect()
    conn.execute("INSERT INTO routines (name, created_at) VALUES (?, ?)", (name, now_iso()))
    conn.commit()
    conn.close()

def rename_routine(routine_id: int, name: str):
    conn = connect()
    conn.execute("UPDATE routines SET name=? WHERE id=?", (name, routine_id))
    conn.commit()
    conn.close()

def delete_routine(routine_id: int):
    conn = connect()
    conn.execute("DELETE FROM routines WHERE id=?", (routine_id,))
    conn.commit()
    conn.close()

# --- Exercises ---
def list_exercises(routine_id: int):
    conn = connect()
    rows = conn.execute("""
        SELECT id, routine_id, name, order_index, default_sets, default_rest_seconds, image_path
        FROM exercises
        WHERE routine_id=?
        ORDER BY order_index ASC, id ASC
    """, (routine_id,)).fetchall()
    conn.close()
    return rows

def add_exercise(routine_id: int, name: str, order_index: int, default_sets: int, default_rest_seconds: int, image_path: str | None):
    conn = connect()
    conn.execute("""
        INSERT INTO exercises (routine_id, name, order_index, default_sets, default_rest_seconds, image_path)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (routine_id, name, order_index, default_sets, default_rest_seconds, image_path))
    conn.commit()
    conn.close()


def update_exercise(exercise_id: int, name: str, order_index: int, default_sets: int, default_rest_seconds: int, image_path: str | None):
    conn = connect()

    if image_path is None:
        # no cambies imagen si no se subió una nueva
        conn.execute("""
            UPDATE exercises
            SET name=?, order_index=?, default_sets=?, default_rest_seconds=?
            WHERE id=?
        """, (name, order_index, default_sets, default_rest_seconds, exercise_id))
    else:
        conn.execute("""
            UPDATE exercises
            SET name=?, order_index=?, default_sets=?, default_rest_seconds=?, image_path=?
            WHERE id=?
        """, (name, order_index, default_sets, default_rest_seconds, image_path, exercise_id))

    conn.commit()
    conn.close()


def delete_exercise(exercise_id: int):
    conn = connect()
    conn.execute("DELETE FROM exercises WHERE id=?", (exercise_id,))
    conn.commit()
    conn.close()

# --- Sessions / Logs ---
def start_session(routine_id: int) -> int:
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO workout_sessions (routine_id, started_at) VALUES (?, ?)", (routine_id, now_iso()))
    session_id = cur.lastrowid
    conn.commit()
    conn.close()
    return int(session_id)

def finish_session(session_id: int):
    conn = connect()
    conn.execute("UPDATE workout_sessions SET finished_at=? WHERE id=?", (now_iso(), session_id))
    conn.commit()
    conn.close()

def log_set(session_id: int, exercise_id: int, set_index: int, reps: int, weight: float):
    conn = connect()
    conn.execute("""
        INSERT INTO set_logs (session_id, exercise_id, set_index, reps, weight, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (session_id, exercise_id, set_index, reps, weight, now_iso()))
    conn.commit()
    conn.close()

def stats_sets():
    conn = connect()
    rows = conn.execute("""
        SELECT
            sl.created_at,
            r.name AS routine,
            e.name AS exercise,
            sl.set_index,
            sl.reps,
            sl.weight,
            (sl.reps * sl.weight) AS volume
        FROM set_logs sl
        JOIN exercises e ON e.id = sl.exercise_id
        JOIN routines r ON r.id = e.routine_id
        ORDER BY sl.created_at DESC
    """).fetchall()
    conn.close()
    return rows


# --- GUARDA IMAGENES ---
def save_exercise_image(uploaded_file) -> str:
    """
    Guarda un archivo subido por Streamlit en assets/exercises/ y devuelve su ruta (str).
    """
    suffix = Path(uploaded_file.name).suffix.lower() if uploaded_file.name else ".png"
    if suffix not in [".png", ".jpg", ".jpeg", ".webp"]:
        suffix = ".png"

    filename = f"{uuid4().hex}{suffix}"
    dest = EXERCISE_IMG_DIR / filename

    # uploaded_file es un UploadedFile (tiene getbuffer())
    with open(dest, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return str(dest).replace("\\", "/")
