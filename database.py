"""
GPTify Meet - Local SQLite Database Layer
Stores meetings, transcriptions, decisions, and tasks locally.
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "gptify_meet.db"

def get_connection() -> sqlite3.Connection:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS meetings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        date TEXT NOT NULL,
        duration TEXT NOT NULL,
        audio_path TEXT,
        summary TEXT NOT NULL,
        attendees TEXT NOT NULL,          -- JSON list
        open_questions TEXT,              -- JSON list
        transcript_text TEXT NOT NULL,
        transcript_segments TEXT NOT NULL,-- JSON list of {time, speaker, text}
        decisions TEXT NOT NULL,          -- JSON list of {text, source_time}
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        meeting_id INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
        text TEXT NOT NULL,
        owner TEXT NOT NULL,
        due_date TEXT NOT NULL,
        completed INTEGER NOT NULL DEFAULT 0
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact TEXT NOT NULL,
        company TEXT,
        meeting_tool TEXT DEFAULT 'Google Meet',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # Check if sample meeting exists; if empty, insert initial sample meeting
    cursor.execute("SELECT COUNT(*) as count FROM meetings")
    if cursor.fetchone()["count"] == 0:
        seed_sample_meeting(cursor)

    conn.commit()
    conn.close()

def seed_sample_meeting(cursor: sqlite3.Cursor):
    sample_segments = [
        {"time": "12:48", "speaker": "Aziza Karimova", "text": "Sinov loyihasini birinchi oktabrdan boshlaymiz. Tijorat taklifini yigirma sakkizinchigacha yuboraman."},
        {"time": "13:06", "speaker": "Sardor Aliyev", "text": "Texnik talablarni o'ttizinchigacha tasdiqlab beraman."},
        {"time": "14:21", "speaker": "Dilshod Rahimov", "text": "Budjetni taklif kelganidan keyin yana ko‘rib chiqamiz."}
    ]
    sample_decisions = [
        {"text": "Sinov loyihasi 1-oktabrda boshlanadi.", "source_time": "12:48"}
    ]
    sample_attendees = ["Aziza Karimova", "Sardor Aliyev", "Dilshod Rahimov"]
    sample_questions = ["Yakuniy budjet hali tasdiqlanmagan."]
    
    cursor.execute("""
    INSERT INTO meetings (
        title, date, duration, summary, attendees, open_questions,
        transcript_text, transcript_segments, decisions
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        "Hamkorlik uchrashuvi",
        "26-sentabr, 2026",
        "32 daqiqa",
        "Jamoa yangi hamkor bilan sinov loyihasi doirasini kelishib oldi. Tijorat taklifi va texnik talablar ish boshlanishidan oldin tasdiqlanadi.",
        json.dumps(sample_attendees, ensure_ascii=False),
        json.dumps(sample_questions, ensure_ascii=False),
        "Aziza Karimova: Sinov loyihasini birinchi oktabrdan boshlaymiz. Tijorat taklifini yigirma sakkizinchigacha yuboraman.\nSardor Aliyev: Texnik talablarni o'ttizinchigacha tasdiqlab beraman.\nDilshod Rahimov: Budjetni taklif kelganidan keyin yana ko'rib chiqamiz.",
        json.dumps(sample_segments, ensure_ascii=False),
        json.dumps(sample_decisions, ensure_ascii=False)
    ))
    meeting_id = cursor.lastrowid
    
    sample_tasks = [
        ("Tijorat taklifini yuborish", "Aziza", "28-sen", 0),
        ("Texnik talablarni tasdiqlash", "Sardor", "30-sen", 0),
        ("Sinov natijalarini ko‘rib chiqish", "Mas’ul yo‘q", "8-okt", 0)
    ]
    for task_text, owner, due, comp in sample_tasks:
        cursor.execute("""
        INSERT INTO tasks (meeting_id, text, owner, due_date, completed)
        VALUES (?, ?, ?, ?, ?)
        """, (meeting_id, task_text, owner, due, comp))

def get_all_meetings(query: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    if query:
        q = f"%{query}%"
        cursor.execute("""
        SELECT m.* FROM meetings m
        WHERE m.title LIKE ? OR m.summary LIKE ? OR m.transcript_text LIKE ?
        ORDER BY m.id DESC
        """, (q, q, q))
    else:
        cursor.execute("SELECT * FROM meetings ORDER BY id DESC")
    rows = cursor.fetchall()
    
    results = []
    for r in rows:
        m_id = r["id"]
        cursor.execute("SELECT * FROM tasks WHERE meeting_id = ?", (m_id,))
        task_rows = cursor.fetchall()
        tasks = [dict(t) for t in task_rows]
        
        results.append({
            "id": r["id"],
            "title": r["title"],
            "date": r["date"],
            "duration": r["duration"],
            "audio_path": r["audio_path"],
            "summary": r["summary"],
            "attendees": json.loads(r["attendees"] or "[]"),
            "open_questions": json.loads(r["open_questions"] or "[]"),
            "transcript_text": r["transcript_text"],
            "transcript_segments": json.loads(r["transcript_segments"] or "[]"),
            "decisions": json.loads(r["decisions"] or "[]"),
            "created_at": r["created_at"],
            "tasks": tasks
        })
    conn.close()
    return results

def get_meeting_by_id(meeting_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    cursor.execute("SELECT * FROM tasks WHERE meeting_id = ?", (meeting_id,))
    task_rows = cursor.fetchall()
    tasks = [dict(t) for t in task_rows]
    
    data = {
        "id": row["id"],
        "title": row["title"],
        "date": row["date"],
        "duration": row["duration"],
        "audio_path": row["audio_path"],
        "summary": row["summary"],
        "attendees": json.loads(row["attendees"] or "[]"),
        "open_questions": json.loads(row["open_questions"] or "[]"),
        "transcript_text": row["transcript_text"],
        "transcript_segments": json.loads(row["transcript_segments"] or "[]"),
        "decisions": json.loads(row["decisions"] or "[]"),
        "created_at": row["created_at"],
        "tasks": tasks
    }
    conn.close()
    return data

def save_meeting(
    title: str,
    date: str,
    duration: str,
    summary: str,
    attendees: List[str],
    open_questions: List[str],
    transcript_text: str,
    transcript_segments: List[Dict[str, str]],
    decisions: List[Dict[str, str]],
    tasks: List[Dict[str, Any]],
    audio_path: Optional[str] = None
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO meetings (
        title, date, duration, summary, attendees, open_questions,
        transcript_text, transcript_segments, decisions, audio_path
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        title,
        date,
        duration,
        summary,
        json.dumps(attendees, ensure_ascii=False),
        json.dumps(open_questions, ensure_ascii=False),
        transcript_text,
        json.dumps(transcript_segments, ensure_ascii=False),
        json.dumps(decisions, ensure_ascii=False),
        audio_path
    ))
    meeting_id = cursor.lastrowid
    
    for t in tasks:
        owner_val = t.get("owner") or "Mas’ul belgilanmagan"
        due_val = t.get("due_date") or "Muddatsiz"
        cursor.execute("""
        INSERT INTO tasks (meeting_id, text, owner, due_date, completed)
        VALUES (?, ?, ?, ?, ?)
        """, (
            meeting_id,
            t.get("text", ""),
            owner_val,
            due_val,
            1 if t.get("completed") else 0
        ))
    
    conn.commit()
    conn.close()
    return meeting_id

def toggle_task(task_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT completed FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    new_status = 0 if row["completed"] else 1
    cursor.execute("UPDATE tasks SET completed = ? WHERE id = ?", (new_status, task_id))
    conn.commit()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    updated_row = dict(cursor.fetchone())
    conn.close()
    return updated_row

def update_meeting(meeting_id: int, title: Optional[str] = None, summary: Optional[str] = None) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    if title and summary:
        cursor.execute("UPDATE meetings SET title = ?, summary = ? WHERE id = ?", (title, summary, meeting_id))
    elif title:
        cursor.execute("UPDATE meetings SET title = ?, WHERE id = ?", (title, meeting_id))
    elif summary:
        cursor.execute("UPDATE meetings SET summary = ? WHERE id = ?", (summary, meeting_id))
    conn.commit()
    conn.close()
    return True

def update_speaker_name(meeting_id: int, old_speaker: str, new_speaker: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT transcript_segments, attendees FROM meetings WHERE id = ?", (meeting_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return False
    
    segments = json.loads(row["transcript_segments"] or "[]")
    for s in segments:
        if s.get("speaker") == old_speaker:
            s["speaker"] = new_speaker
            
    attendees = json.loads(row["attendees"] or "[]")
    attendees = [new_speaker if a == old_speaker else a for a in attendees]
    if new_speaker not in attendees:
        attendees.append(new_speaker)
        
    cursor.execute("""
        UPDATE meetings SET transcript_segments = ?, attendees = ? WHERE id = ?
    """, (json.dumps(segments, ensure_ascii=False), json.dumps(attendees, ensure_ascii=False), meeting_id))
    conn.commit()
    conn.close()
    return True

def add_task(meeting_id: int, text: str, owner: str = "Mas’ul belgilanmagan", due_date: str = "Bugun") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tasks (meeting_id, text, owner, due_date, completed)
        VALUES (?, ?, ?, ?, 0)
    """, (meeting_id, text, owner, due_date))
    task_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    new_t = dict(cursor.fetchone())
    conn.close()
    return new_t

def delete_task(task_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success

def delete_meeting(meeting_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT audio_path FROM meetings WHERE id = ?", (meeting_id,))
    row = cursor.fetchone()
    if row and row["audio_path"]:
        p = Path(row["audio_path"])
        if p.exists():
            try:
                p.unlink()
            except Exception:
                pass
    cursor.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_settings() -> Dict[str, str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM settings")
    settings = {row["key"]: row["value"] for row in cursor.fetchall()}
    conn.close()
    # Default settings
    default = {
        "retention": "manual", # manual, 30, 90
        "mode": "local",       # local, cloud
        "theme": "light"
    }
    default.update(settings)
    return default

def save_setting(key: str, value: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO settings (key, value) VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()
    conn.close()

def save_lead(name: str, contact: str, company: Optional[str] = None, meeting_tool: Optional[str] = "Google Meet") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO leads (name, contact, company, meeting_tool)
    VALUES (?, ?, ?, ?)
    """, (name, contact, company or "", meeting_tool or "Google Meet"))
    lead_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lead_id

def get_all_leads() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM leads ORDER BY created_at DESC")
    rows = cursor.fetchall()
    leads = [dict(row) for row in rows]
    conn.close()
    return leads

