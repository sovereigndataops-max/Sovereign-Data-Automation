"""Personal Assistant v0.1: offline project memory for Python + SQLite.

Phone-friendly command menu. No AI, API, cloud, automation, or third-party packages.
Run: python Assistant.py
Database and backups stay beside this script. Do NOT mix databases from other drafts.
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_PATH = APP_DIR / "assistant.db"
BACKUP_DIR = APP_DIR / "backup"

# Database shape guard: don't accidentally open an incompatible AI draft.
EXPECTED_COLUMNS = {
    "projects": {"id", "name", "description", "status", "created_at"},
    "notes": {"id", "project_id", "text", "source", "created_at"},
    "decisions": {"id", "project_id", "decision", "status", "source", "supersedes_id", "created_at"},
    "tasks": {"id", "project_id", "task", "status", "created_at", "completed_at"},
}


def timestamp():
    """UTC timestamp for reliable chronological sorting across time changes."""
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def connect(path=DB_PATH):
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def initialize(conn):
    """Initialize only a blank DB or this exact schema; don't modify others."""
    existing = {row[0].lower() for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )}
    expected = set(EXPECTED_COLUMNS)
    if existing and existing != expected:
        raise RuntimeError("Different database structure detected. Keep each AI version "
                           "in its own folder; no existing data was changed.")
    if existing:
        for table, columns in EXPECTED_COLUMNS.items():
            current = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
            if current != columns:
                raise RuntimeError("Incompatible assistant.db found. Do not mix AI versions. "
                                   "Your existing data has not been changed.")
        if conn.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise RuntimeError("Unrecognized database version. Existing data was not changed.")
        required_triggers = {"decisions_never_update", "decisions_never_delete",
                             "tasks_never_delete", "decisions_same_project"}
        installed_triggers = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger'")}
        if not required_triggers.issubset(installed_triggers):
            raise RuntimeError("Decision/task protections are missing. Database left untouched.")
        return

    conn.executescript("""
        BEGIN;
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE COLLATE NOCASE CHECK(length(trim(name)) > 0),
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Active'
                CHECK(status IN ('Active', 'Archived')),
            created_at TEXT NOT NULL
        );
        CREATE TABLE notes (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
            text TEXT NOT NULL CHECK(length(trim(text)) > 0),
            source TEXT NOT NULL CHECK(length(trim(source)) > 0),
            created_at TEXT NOT NULL
        );
        CREATE TABLE decisions (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
            decision TEXT NOT NULL CHECK(length(trim(decision)) > 0),
            status TEXT NOT NULL DEFAULT 'Active'
                CHECK(status IN ('Active', 'Rejected')),
            source TEXT NOT NULL CHECK(length(trim(source)) > 0),
            supersedes_id INTEGER UNIQUE REFERENCES decisions(id) ON DELETE RESTRICT,
            created_at TEXT NOT NULL,
            CHECK(supersedes_id IS NULL OR status = 'Active')
        );
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY,
            project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
            task TEXT NOT NULL CHECK(length(trim(task)) > 0),
            status TEXT NOT NULL DEFAULT 'Open'
                CHECK(status IN ('Open', 'Done')),
            created_at TEXT NOT NULL,
            completed_at TEXT,
            CHECK((status = 'Open' AND completed_at IS NULL)
                  OR (status = 'Done' AND completed_at IS NOT NULL))
        );
        CREATE INDEX idx_notes_project ON notes(project_id);
        CREATE INDEX idx_decisions_project ON decisions(project_id);
        CREATE INDEX idx_tasks_project ON tasks(project_id);
        CREATE TRIGGER decisions_never_update BEFORE UPDATE ON decisions
            BEGIN SELECT RAISE(ABORT, 'Decision history is immutable'); END;
        CREATE TRIGGER decisions_never_delete BEFORE DELETE ON decisions
            BEGIN SELECT RAISE(ABORT, 'Decision history is immutable'); END;
        CREATE TRIGGER tasks_never_delete BEFORE DELETE ON tasks
            BEGIN SELECT RAISE(ABORT, 'Task history cannot be deleted'); END;
        CREATE TRIGGER decisions_same_project BEFORE INSERT ON decisions
            WHEN NEW.supersedes_id IS NOT NULL
            BEGIN
                SELECT CASE WHEN NOT EXISTS (
                    SELECT 1 FROM decisions old
                    WHERE old.id = NEW.supersedes_id
                      AND old.project_id = NEW.project_id
                      AND old.status = 'Active'
                ) THEN RAISE(ABORT, 'Replacement must be an active decision in the same project') END;
            END;
        PRAGMA user_version = 1;
        COMMIT;
    """)


def add_project(conn, name, description=""):
    name = name.strip()
    if not name:
        raise ValueError("Project name required")
    with conn:
        return conn.execute(
            "INSERT INTO projects(name,description,created_at) VALUES(?,?,?)",
            (name, description.strip(), timestamp())
        ).lastrowid


def add_note(conn, project_id, text, source="Tina"):
    if not text.strip() or not source.strip():
        raise ValueError("Note and source required")
    with conn:
        return conn.execute(
            "INSERT INTO notes(project_id,text,source,created_at) VALUES(?,?,?,?)",
            (project_id, text.strip(), source.strip(), timestamp())
        ).lastrowid


def add_decision(conn, project_id, decision, source="Tina", status="Active", supersedes_id=None):
    """Append only. 'Superseded' is CALCULATED, never written to old decision."""
    if not decision.strip() or not source.strip():
        raise ValueError("Decision and source required")
    if status not in ("Active", "Rejected"):
        raise ValueError("Decision must be Active or Rejected")
    if supersedes_id is not None:
        if status != "Active":
            raise ValueError("A replacement must be Active")
        old = conn.execute("""
            SELECT old.id FROM decisions old
            LEFT JOIN decisions new ON new.supersedes_id = old.id
            WHERE old.id=? AND old.project_id=? AND old.status='Active'
              AND new.id IS NULL
        """, (supersedes_id, project_id)).fetchone()
        if old is None:
            raise ValueError("Decision is not active in the selected project")
    with conn:
        return conn.execute("""
            INSERT INTO decisions(project_id,decision,status,source,supersedes_id,created_at)
            VALUES(?,?,?,?,?,?)
        """, (project_id, decision.strip(), status, source.strip(), supersedes_id,
              timestamp())).lastrowid


def add_task(conn, project_id, task):
    if not task.strip():
        raise ValueError("Task required")
    with conn:
        return conn.execute("""
            INSERT INTO tasks(project_id,task,status,created_at)
            VALUES(?,?,'Open',?)
        """, (project_id, task.strip(), timestamp())).lastrowid


def complete_task(conn, project_id, task_id):
    """Refuse cross-project IDs and repeated completion."""
    with conn:
        updated = conn.execute("""
            UPDATE tasks SET status='Done', completed_at=?
            WHERE id=? AND project_id=? AND status='Open'
        """, (timestamp(), task_id, project_id))
        return updated.rowcount == 1


def decision_rows(conn, project_id):
    """Effective status: never update the historical decision itself."""
    return conn.execute("""
        SELECT d.*, CASE
            WHEN newer.id IS NOT NULL THEN 'Superseded'
            ELSE d.status END AS effective_status
        FROM decisions d
        LEFT JOIN decisions newer ON newer.supersedes_id=d.id
        WHERE d.project_id=? ORDER BY d.id
    """, (project_id,)).fetchall()


def dashboard(conn, project_id):
    project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if project is None:
        raise ValueError("Project not found")
    notes = conn.execute("SELECT * FROM notes WHERE project_id=? ORDER BY id DESC",
                         (project_id,)).fetchall()
    decisions = decision_rows(conn, project_id)
    tasks = conn.execute("SELECT * FROM tasks WHERE project_id=? ORDER BY id",
                         (project_id,)).fetchall()
    # Activity is scoped to the selected project and limited for phone display.
    recent = conn.execute("""
        SELECT 'Note' AS kind, text AS detail, created_at AS when_at FROM notes WHERE project_id=?
        UNION ALL
        SELECT 'Decision', decision, created_at FROM decisions WHERE project_id=?
        UNION ALL
        SELECT 'Task', task, COALESCE(completed_at, created_at) FROM tasks WHERE project_id=?
        ORDER BY when_at DESC LIMIT 10
    """, (project_id, project_id, project_id)).fetchall()
    return {
        "project": project,
        "notes": notes,
        "decisions": decisions,
        "tasks": tasks,
        "open_count": sum(t["status"] == "Open" for t in tasks),
        "active_count": sum(d["effective_status"] == "Active" for d in decisions),
        "note_count": len(notes),
        "recent": recent,
    }


def _like_pattern(text):
    return "%" + text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def search_memory(conn, keyword, project_id=None):
    """Cross-project search is deliberately labeled with a project name.

    Pass project_id to restrict search to ONE project.
    """
    if not keyword.strip():
        return []
    pattern = _like_pattern(keyword.strip())
    results = []
    scope = " AND p.id=?" if project_id is not None else ""
    params = (pattern, project_id) if project_id is not None else (pattern,)

    for kind, table, field in (
        ("Note", "notes", "text"),
        ("Decision", "decisions", "decision"),
        ("Task", "tasks", "task"),
    ):
        sql = (f"SELECT p.name AS project, t.id, t.{field} AS detail "
               f"FROM {table} t JOIN projects p ON t.project_id=p.id "
               f"WHERE t.{field} LIKE ? ESCAPE '\\'{scope} ORDER BY p.name, t.id")
        for row in conn.execute(sql, params):
            results.append((kind, row["project"], row["id"], row["detail"]))
    sql = ("SELECT p.name AS project, p.id, p.description AS detail FROM projects p "
           "WHERE (p.name LIKE ? ESCAPE '\\' OR p.description LIKE ? ESCAPE '\\')" + scope +
           " ORDER BY p.name")
    pparams = (pattern, pattern, project_id) if project_id is not None else (pattern, pattern)
    for row in conn.execute(sql, pparams):
        results.append(("Project", row["project"], row["id"], row["detail"]))
    return sorted(results, key=lambda r: (r[1].lower(), r[0], r[2]))


def backup_database(conn, directory=None):
    """SQLite's consistent online backup, followed by an integrity check."""
    directory = Path(directory) if directory is not None else BACKUP_DIR
    directory.mkdir(parents=True, exist_ok=True)
    filename = "assistant_backup_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f") + ".db"
    target = directory / filename
    conn.commit()
    try:
        with sqlite3.connect(str(target)) as dest:
            conn.backup(dest)
            result = dest.execute("PRAGMA integrity_check").fetchone()[0]
            if result != "ok":
                raise RuntimeError("Backup integrity check failed")
    except Exception:
        if target.exists():
            target.unlink()
        raise
    return target


def choose_project(conn):
    rows = conn.execute("SELECT id,name FROM projects ORDER BY name").fetchall()
    if not rows:
        print("No projects yet. Add a project first.")
        return None
    print("\nPROJECTS")
    for row in rows:
        print(f" {row['id']}. {row['name']}")
    raw = input("Project number (Enter cancels): ").strip()
    if not raw:
        return None
    try:
        chosen = int(raw)
    except ValueError:
        print("Enter a number.")
        return None
    if chosen not in {row["id"] for row in rows}:
        print("That project does not exist.")
        return None
    return chosen


def read_source():
    return input("Source (Enter = Tina): ").strip() or "Tina"


def show_dashboard(conn, project_id):
    data = dashboard(conn, project_id)
    p = data["project"]
    print(f"\n=== {p['name']} [{p['status']}] ===")
    if p["description"]:
        print(p["description"])
    print(f"Open tasks: {data['open_count']} | Active decisions: {data['active_count']} | Notes: {data['note_count']}")
    print("\nACTIVE DECISIONS")
    active = [d for d in data["decisions"] if d["effective_status"] == "Active"]
    for d in active:
        print(f" #{d['id']} {d['decision']} [source: {d['source']}]")
    if not active:
        print(" (none)")
    print("\nTASKS")
    for t in data["tasks"]:
        print(f" #{t['id']} [{t['status']}] {t['task']}")
    if not data["tasks"]:
        print(" (none)")
    print("\nRECENT NOTES (up to 10)")
    for n in data["notes"][:10]:
        print(f" #{n['id']} {n['text']} [source: {n['source']}]")
    if not data["notes"]:
        print(" (none)")
    past = [d for d in data["decisions"] if d["effective_status"] != "Active"]
    if past:
        print("\nDECISION HISTORY (last 10)")
        for d in past[-10:]:
            print(f" #{d['id']} [{d['effective_status']}] {d['decision']}")
    print("\nLAST 10 ACTIVITIES")
    for r in data["recent"]:
        print(f" {r['kind']}: {r['detail']}")
    if not data["recent"]:
        print(" (none)")
    print()


def main():
    conn = connect()
    try:
        initialize(conn)
        while True:
            print("""
PERSONAL ASSISTANT v0.1 — OFFLINE
 1 Add Project
 2 Add Note
 3 Add Decision
 4 Add Task
 5 Complete Task
 6 Change Decision (keeps history)
 7 Search Memory
 8 View Project Dashboard
 9 Backup Database
 0 Exit""")
            choice = input("Choose number: ").strip()
            try:
                if choice == "0":
                    print("Saved. Goodbye.")
                    return
                if choice == "1":
                    name = input("Project name: ")
                    description = input("Description (optional): ")
                    print(f"Created project #{add_project(conn, name, description)}.")
                    continue
                if choice == "9":
                    print(f"Verified backup saved: {backup_database(conn)}")
                    continue
                if choice == "7":
                    word = input("Search word or phrase: ")
                    scope = input("All projects? [Y/n]: ").strip().lower()
                    pid = None if scope != "n" else choose_project(conn)
                    if scope == "n" and pid is None:
                        continue
                    matches = search_memory(conn, word, pid)
                    for kind, project, row_id, detail in matches:
                        print(f" [{project}] {kind} #{row_id}: {detail}")
                    if not matches:
                        print("No matches.")
                    continue
                if choice not in {"2", "3", "4", "5", "6", "8"}:
                    print("Unknown option.")
                    continue
                pid = choose_project(conn)
                if pid is None:
                    continue
                if choice == "2":
                    content = input("Note: ")
                    source = read_source()
                    print(f"Saved note #{add_note(conn, pid, content, source)}.")
                elif choice == "3":
                    content = input("Decision: ")
                    source = read_source()
                    decision_type = input("Approve or Reject? [A/r]: ").strip().lower()
                    status = "Rejected" if decision_type == "r" else "Active"
                    confirmation = "REJECT" if status == "Rejected" else "APPROVE"
                    if input(f"Type {confirmation} to save: ").strip() == confirmation:
                        print(f"Saved {status.lower()} decision #{add_decision(conn, pid, content, source, status)}.")
                    else:
                        print("Cancelled; nothing saved.")
                elif choice == "4":
                    print(f"Saved task #{add_task(conn, pid, input('Task: '))} [Open].")
                elif choice == "5":
                    open_tasks = [t for t in dashboard(conn, pid)["tasks"] if t["status"] == "Open"]
                    for t in open_tasks:
                        print(f" #{t['id']}. {t['task']}")
                    if not open_tasks:
                        print("No open tasks.")
                        continue
                    task_id = int(input("Task number to complete: "))
                    print("Task completed." if complete_task(conn, pid, task_id)
                          else "No matching open task in this project.")
                elif choice == "6":
                    active = [d for d in decision_rows(conn, pid) if d["effective_status"] == "Active"]
                    for d in active:
                        print(f" #{d['id']}. {d['decision']}")
                    if not active:
                        print("No active decisions to change.")
                        continue
                    old_id = int(input("Decision number to replace: "))
                    if old_id not in {d["id"] for d in active}:
                        print("No active decision with that number in this project.")
                        continue
                    content = input("New decision: ")
                    source = read_source()
                    if input("Type APPROVE to confirm replacement: ").strip() == "APPROVE":
                        new_id = add_decision(conn, pid, content, source, "Active", old_id)
                        print(f"Saved decision #{new_id}. Old decision #{old_id} remains in history.")
                    else:
                        print("Cancelled; no changes.")
                elif choice == "8":
                    show_dashboard(conn, pid)
            except (ValueError, sqlite3.IntegrityError) as err:
                print(f"Action not saved: {err}")
            except sqlite3.Error as err:
                print(f"Database error: {err}")
    finally:
        conn.close()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nClosed. Saved records remain on your device.")
    except (RuntimeError, sqlite3.DatabaseError) as err:
        print(f"Cannot open database: {err}")

