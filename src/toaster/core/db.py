import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager

class SQLiteCache:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True)
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Yields a SQLite connection optimized for concurrent swarm reads/writes."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Initializes the database schema and enables WAL mode."""
        with self.get_connection() as conn:
            # Enable Write-Ahead Logging for concurrent agent swarms
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            
            # Files Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id TEXT PRIMARY KEY,
                    ufid TEXT UNIQUE NOT NULL,
                    source_path TEXT,
                    imports JSON
                )
            """)

            # Classes Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS classes (
                    id TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    parent_class_id TEXT,
                    ucid TEXT UNIQUE NOT NULL,
                    signature TEXT,
                    body TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    description TEXT,
                    constants JSON,
                    FOREIGN KEY(file_id) REFERENCES files(id),
                    FOREIGN KEY(parent_class_id) REFERENCES classes(id)
                )
            """)

            # Methods Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS methods (
                    id TEXT PRIMARY KEY,
                    class_id TEXT,
                    file_id TEXT,
                    identifier TEXT,
                    scoped_identifier TEXT,
                    return_type TEXT,
                    umid TEXT UNIQUE NOT NULL,
                    signature TEXT,
                    body TEXT,
                    body_hash TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    parameters JSON,
                    dependencies JSON,
                    inbound_dependencies JSON,
                    description TEXT,
                    FOREIGN KEY(class_id) REFERENCES classes(id),
                    FOREIGN KEY(file_id) REFERENCES files(id)
                )
            """)

            # Fields Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fields (
                    id TEXT PRIMARY KEY,
                    class_id TEXT,
                    file_id TEXT,
                    ucid TEXT UNIQUE NOT NULL,
                    name TEXT,
                    signature TEXT,
                    field_type TEXT,
                    FOREIGN KEY(class_id) REFERENCES classes(id),
                    FOREIGN KEY(file_id) REFERENCES files(id)
                )
            """)

            # Indexes for querying speed
            conn.execute("CREATE INDEX IF NOT EXISTS idx_classes_file ON classes(file_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_methods_class ON methods(class_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_methods_file ON methods(file_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_methods_identifier ON methods(identifier)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fields_class ON fields(class_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_fields_file ON fields(file_id)")
            
            conn.commit()
