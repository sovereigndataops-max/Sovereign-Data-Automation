import glob
import sqlite3

backups = glob.glob("backup/*.db")
assert backups, "No backup found"

source = sqlite3.connect(backups[-1])
restored = sqlite3.connect(":memory:")

source.backup(restored)

result = restored.execute(
    "PRAGMA integrity_check"
).fetchone()[0]
assert result == "ok", "Restore failed"

projects = restored.execute(
    "SELECT COUNT(*) FROM projects"
).fetchone()[0]
assert projects > 0, "Projects missing"

print("RESTORE VERIFIED")

source.close()
restored.close()

