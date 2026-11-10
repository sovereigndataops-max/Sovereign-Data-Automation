"""Windows executable entry point; stores user data beside the executable."""
import sys
from pathlib import Path
import Assistant

if __name__ == "__main__":
    app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    Assistant.APP_DIR = app_dir
    Assistant.DB_PATH = app_dir / "assistant.db"
    Assistant.BACKUP_DIR = app_dir / "backup"
    # The existing connect() function captures DB_PATH in its default argument.
    Assistant.connect.__defaults__ = (Assistant.DB_PATH,)
    Assistant.main()
