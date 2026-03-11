from collections import defaultdict
from typing import List, Dict, Optional
import json
from pathlib import Path

from toaster.core.db import SQLiteCache

class MemberRegistry:
    def __init__(self, project_dir: str):
        self.db_path = Path(project_dir) / ".toaster.db"
        self.db = SQLiteCache(self.db_path)
        
        # Keep in-memory representations for active parsing/traversal
        self.map_umid: Dict[str, "BaseMethod"] = {}
        self.map_scoped: Dict[str, List["BaseMethod"]] = defaultdict(list)
        self.map_short: Dict[str, List["BaseMethod"]] = defaultdict(list)
        self.map_class = {}
        self.map_id: Dict[str, "BaseStruct"] = {}
    
    def add_method(self, method):
        self.map_umid[method.umid] = method
        self.map_id[method.id] = method
        self.map_scoped[method.scoped_identifier].append(method)
        self.map_short[method.identifier].append(method)
    
    def add_class(self, class_obj):
        self.map_class[class_obj.ucid] = class_obj
        self.map_id[class_obj.id] = class_obj
        
    def add_file(self, file_obj):
        # Optional: Track files in memory if needed
        pass

    def save_to_db(self, files: List["BaseFile"]):
        """Flush the parsed AST graph to the SQLite database."""
        with self.db.get_connection() as conn:
            for file in files:
                source_path_str = str(getattr(file, "source_path", ""))
                conn.execute(
                    "INSERT INTO files (id, ufid, source_path, imports) VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET source_path=excluded.source_path, imports=excluded.imports",
                    (file.id, file.ufid, source_path_str, json.dumps(file.imports))
                )
                
                for class_obj in file.classes:
                    self._save_class_recursive(conn, class_obj, file.id)

            conn.commit()

    def _save_class_recursive(self, conn, class_obj, file_id, parent_id=None):
        conn.execute(
            """INSERT INTO classes 
               (id, file_id, parent_class_id, ucid, signature, body, start_line, end_line, description, constants)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET 
               signature=excluded.signature, body=excluded.body, description=COALESCE(excluded.description, classes.description)
            """,
            (class_obj.id, file_id, parent_id, class_obj.ucid, class_obj.signature, class_obj.body, 
             class_obj.start_line, class_obj.end_line, class_obj.description, json.dumps(class_obj.constants))
        )
        
        for method in class_obj.methods.values():
            conn.execute(
                """INSERT INTO methods
                   (id, class_id, identifier, scoped_identifier, return_type, umid, signature, body, body_hash, start_line, end_line, parameters, dependencies, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                   signature=excluded.signature, body=excluded.body, body_hash=excluded.body_hash, dependencies=excluded.dependencies, description=COALESCE(excluded.description, methods.description)
                """,
                (method.id, class_obj.id, method.identifier, method.scoped_identifier, method.return_type, 
                 method.umid, method.signature, method.body, method.body_hash, method.start_line, method.end_line, 
                 json.dumps(method.parameters), json.dumps(method.dependency_names), method.description)
            )
            
        for child_class in class_obj.child_classes.values():
            self._save_class_recursive(conn, child_class, file_id, class_obj.id)

    def load_cache(self):
        """Loads descriptions from the SQLite database back into the active memory graph."""
        with self.db.get_connection() as conn:
            # Load methods
            rows = conn.execute("SELECT umid, body_hash, description FROM methods WHERE description IS NOT NULL").fetchall()
            for row in rows:
                method = self.map_umid.get(row['umid'])
                if method and method.body_hash == row['body_hash']:
                    method.description = row['description']
                    
            # Load classes
            rows = conn.execute("SELECT ucid, description FROM classes WHERE description IS NOT NULL").fetchall()
            for row in rows:
                class_obj = self.map_class.get(row['ucid'])
                if class_obj:
                    class_obj.description = row['description']

    def update_method_description(self, method):
        """Used by the LLM client to update descriptions in real-time."""
        with self.db.get_connection() as conn:
            conn.execute("UPDATE methods SET description = ? WHERE id = ?", (method.description, method.id))
            conn.commit()
            
    def update_class_description(self, class_obj):
        """Used by the LLM client to update descriptions in real-time."""
        with self.db.get_connection() as conn:
            conn.execute("UPDATE classes SET description = ? WHERE id = ?", (class_obj.description, class_obj.id))
            conn.commit()

    def get_struct_by_id(self, id: str) -> Optional["BaseStruct"]:
        return self.map_id.get(id, None)

    def get_struct_from_db(self, id: str) -> Optional[dict]:
        """Direct SQLite lookup without memory cache parsing."""
        with self.db.get_connection() as conn:
            if id.startswith("M-"):
                query = """
                    SELECT m.*, c.ucid as _class_ucid, f.source_path as _file_source_path
                    FROM methods m
                    JOIN classes c ON m.class_id = c.id
                    JOIN files f ON c.file_id = f.id
                    WHERE m.id = ?
                """
                row = conn.execute(query, (id,)).fetchone()
            elif id.startswith("C-"):
                row = conn.execute("SELECT * FROM classes WHERE id = ?", (id,)).fetchone()
            elif id.startswith("F-"):
                row = conn.execute("SELECT * FROM files WHERE id = ?", (id,)).fetchone()
            else:
                return None
            
            if row:
                row_dict = dict(row)
                for json_field in ['imports', 'constants', 'parameters', 'dependencies']:
                    if json_field in row_dict and row_dict[json_field]:
                        try:
                            row_dict[json_field] = json.loads(row_dict[json_field])
                        except:
                            pass
                return row_dict
            return None