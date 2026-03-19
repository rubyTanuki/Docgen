from collections import defaultdict
from typing import List, Dict, Optional, Any, TYPE_CHECKING
import json
from pathlib import Path

from toaster.core.db import SQLiteCache
from toaster.core.models import BaseFile, BaseClass, BaseMethod

if TYPE_CHECKING:
    from toaster.core.models import BaseStruct

class RegistryMemoryState:
    """Handles in-memory tracking of the active parsing/traversal graph."""
    def __init__(self):
        self.map_umid: Dict[str, "BaseMethod"] = {}
        self.map_scoped: Dict[str, List["BaseMethod"]] = defaultdict(list)
        self.map_short: Dict[str, List["BaseMethod"]] = defaultdict(list)
        self.map_class: Dict[str, "BaseClass"] = {}
        self.map_id: Dict[str, "BaseStruct"] = {}

    def add_method(self, method: "BaseMethod"):
        self.map_umid[method.umid] = method
        self.map_id[method.id] = method
        self.map_scoped[method.scoped_identifier].append(method)
        self.map_short[method.identifier].append(method)

    def add_class(self, class_obj: "BaseClass"):
        self.map_class[class_obj.ucid] = class_obj
        self.map_id[class_obj.id] = class_obj

class RegistryStorage:
    """Handles persistence of the AST graph and metadata to the SQLite database."""
    def __init__(self, db: SQLiteCache):
        self.db = db

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
                   (id, class_id, identifier, scoped_identifier, return_type, umid, signature, body, body_hash, start_line, end_line, parameters, dependencies, inbound_dependencies, description)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                   signature=excluded.signature, body=excluded.body, body_hash=excluded.body_hash, dependencies=excluded.dependencies, inbound_dependencies=excluded.inbound_dependencies, description=COALESCE(excluded.description, methods.description)
                """,
                (method.id, class_obj.id, method.identifier, method.scoped_identifier, method.return_type, 
                 method.umid, method.signature, method.body, method.body_hash, method.start_line, method.end_line, 
                 json.dumps(method.parameters), json.dumps(method.dependencies), json.dumps(method.inbound_dependencies), method.description)
            )
            
        for child_class in class_obj.child_classes.values():
            self._save_class_recursive(conn, child_class, file_id, class_obj.id)

    def update_method_description(self, method: "BaseMethod"):
        """Used by the LLM client to update descriptions in real-time."""
        with self.db.get_connection() as conn:
            conn.execute("UPDATE methods SET description = ? WHERE id = ?", (method.description, method.id))
            conn.commit()
            
    def update_class_description(self, class_obj: "BaseClass"):
        """Used by the LLM client to update descriptions in real-time."""
        with self.db.get_connection() as conn:
            conn.execute("UPDATE classes SET description = ? WHERE id = ?", (class_obj.description, class_obj.id))
            conn.commit()

class RegistryHydrator:
    """Handles loading and reconstructing objects from the database."""
    def __init__(self, db: SQLiteCache):
        self.db = db

    def load_cache_into_state(self, state: RegistryMemoryState):
        """Loads descriptions from the SQLite database back into the active memory graph."""
        with self.db.get_connection() as conn:
            # Load methods
            rows = conn.execute("SELECT umid, body_hash, description FROM methods WHERE description IS NOT NULL").fetchall()
            for row in rows:
                method = state.map_umid.get(row['umid'])
                if method and method.body_hash == row['body_hash']:
                    method.description = row['description']
                    
            # Load classes
            rows = conn.execute("SELECT ucid, description FROM classes WHERE description IS NOT NULL").fetchall()
            for row in rows:
                class_obj = state.map_class.get(row['ucid'])
                if class_obj:
                    class_obj.description = row['description']

    def get_struct_from_db(self, id: str) -> Optional["BaseStruct"]:
        """Direct SQLite lookup that returns hydrated BaseStruct objects."""
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
                if not row: return None
                return BaseMethod.from_dict(self._parse_row(row))
                
            elif id.startswith("C-"):
                query = """
                    SELECT c.*, f.source_path as _file_source_path
                    FROM classes c
                    JOIN files f ON c.file_id = f.id
                    WHERE c.id = ?
                """
                row = conn.execute(query, (id,)).fetchone()
                if not row: return None
                row_dict = self._parse_row(row)
                
                m_rows = conn.execute("SELECT * FROM methods WHERE class_id = ?", (id,)).fetchall()
                row_dict["methods"] = [self._parse_row(r) for r in m_rows]
                
                c_rows = conn.execute("SELECT * FROM classes WHERE parent_class_id = ?", (id,)).fetchall()
                row_dict["child_classes"] = [self._parse_row(c) for c in c_rows]
                return BaseClass.from_dict(row_dict)
                
            elif id.startswith("F-"):
                row = conn.execute("SELECT * FROM files WHERE id = ?", (id,)).fetchone()
                if not row: return None
                row_dict = self._parse_row(row)
                c_rows = conn.execute("SELECT * FROM classes WHERE file_id = ? AND parent_class_id IS NULL", (id,)).fetchall()
                row_dict["classes"] = [self._parse_row(c) for c in c_rows]
                return BaseFile.from_dict(row_dict)
                
            return None

    def get_files_by_path(self, subpath: str) -> List["BaseFile"]:
        """Direct SQLite lookup that returns hydrated BaseFile objects for a given path prefix."""
        with self.db.get_connection() as conn:
            if subpath == "." or subpath == "./":
                query_path = ""
            elif subpath.startswith("./"):
                query_path = subpath[2:]
            else:
                query_path = subpath
                
            query = "SELECT * FROM files WHERE source_path LIKE ?"
            rows = conn.execute(query, (f"{query_path}%",)).fetchall()
            
            results = []
            for row in rows:
                row_dict = self._parse_row(row)
                c_rows = conn.execute("SELECT * FROM classes WHERE file_id = ? AND parent_class_id IS NULL", (row_dict['id'],)).fetchall()
                class_dicts = []
                for c_row in c_rows:
                    c_dict = self._parse_row(c_row)
                    m_rows = conn.execute("SELECT * FROM methods WHERE class_id = ?", (c_dict['id'],)).fetchall()
                    c_dict["methods"] = [self._parse_row(r) for r in m_rows]
                    c_dict["child_classes"] = []
                    class_dicts.append(c_dict)
                row_dict["classes"] = class_dicts
                results.append(BaseFile.from_dict(row_dict))
                
            return results

    def resolve_name(self, name: str) -> List[Dict[str, Any]]:
        """Queries the SQLite database for structs matching a given name."""
        results = []
        with self.db.get_connection() as conn:
            # Search files
            f_rows = conn.execute(
                "SELECT id, source_path as signature FROM files WHERE ufid LIKE ? OR source_path LIKE ?",
                (f"%{name}%", f"%{name}%")
            ).fetchall()
            for r in f_rows:
                results.append({"id": r["id"], "type": "File", "signature": r["signature"], "description": ""})
            
            # Search classes
            c_rows = conn.execute(
                "SELECT id, signature, description FROM classes WHERE ucid LIKE ?",
                (f"%{name}%",)
            ).fetchall()
            for r in c_rows:
                results.append({"id": r["id"], "type": "Class", "signature": r["signature"], "description": r["description"]})
             
            # Search methods
            m_rows = conn.execute(
                "SELECT id, signature, description FROM methods WHERE identifier LIKE ? OR scoped_identifier LIKE ? OR umid LIKE ?",
                (f"%{name}%", f"%{name}%", f"%{name}%")
            ).fetchall()
            for r in m_rows:
                results.append({"id": r["id"], "type": "Method", "signature": r["signature"], "description": r["description"]})
                
        return results

    @staticmethod
    def _parse_row(row: Any) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        
        row_dict = dict(row)
        json_fields = {
            'imports', 'constants', 'parameters', 
            'dependencies', 'inbound_dependencies'
        }
        
        for field in json_fields:
            if field in row_dict and row_dict[field]:
                try:
                    row_dict[field] = json.loads(row_dict[field])
                except (json.JSONDecodeError, TypeError):
                    pass
                    
        return row_dict

class MemberRegistry:
    """
    A facade class that coordinates in-memory state, storage, and hydration.
    Maintains the existing API for backward compatibility.
    """
    def __init__(self, project_dir: str = "."):
        self.db_path = Path(project_dir) / ".toaster.db"
        self.db = SQLiteCache(self.db_path)
        
        self.state = RegistryMemoryState()
        self.storage = RegistryStorage(self.db)
        self.hydrator = RegistryHydrator(self.db)
    
    @property
    def map_umid(self): return self.state.map_umid
    @property
    def map_scoped(self): return self.state.map_scoped
    @property
    def map_short(self): return self.state.map_short
    @property
    def map_class(self): return self.state.map_class
    @property
    def map_id(self): return self.state.map_id

    def add_method(self, method: "BaseMethod"):
        self.state.add_method(method)
    
    def add_class(self, class_obj: "BaseClass"):
        self.state.add_class(class_obj)
        
    def add_file(self, file_obj: "BaseFile"):
        pass

    def save_to_db(self, files: List["BaseFile"]):
        self.storage.save_to_db(files)

    def load_cache(self):
        self.hydrator.load_cache_into_state(self.state)

    def update_method_description(self, method: "BaseMethod"):
        self.storage.update_method_description(method)
            
    def update_class_description(self, class_obj: "BaseClass"):
        self.storage.update_class_description(class_obj)

    def get_struct_by_id(self, id: str) -> Optional["BaseStruct"]:
        # Check memory first, then DB
        if val := self.state.map_id.get(id):
            return val
        return self.get_struct_from_db(id)

    def get_struct_from_db(self, id: str) -> Optional["BaseStruct"]:
        return self.hydrator.get_struct_from_db(id)

    def get_files_by_path(self, subpath: str) -> List["BaseFile"]:
        return self.hydrator.get_files_by_path(subpath)

    def resolve_name(self, name: str) -> List[Dict[str, Any]]:
        return self.hydrator.resolve_name(name)
