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
                 json.dumps(method.parameters), json.dumps(method.dependencies), method.description)
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

    def _parse_row(self, row, is_method=False):
        if not row: return None
        row_dict = dict(row)
        for json_field in ['imports', 'constants', 'parameters', 'dependencies']:
            if json_field in row_dict and row_dict[json_field]:
                try:
                    row_dict[json_field] = json.loads(row_dict[json_field])
                except Exception:
                    pass
        return row_dict

    def _create_method(self, d: dict) -> "BaseMethod":
        from toaster.languages.java.models import JavaMethod
        from toaster.languages.csharp.models import CSharpMethod
        
        path = d.get("_file_source_path", "")
        method_cls = CSharpMethod if path.endswith(".cs") else JavaMethod
        
        m = method_cls(
            identifier=d['identifier'],
            scoped_identifier=d['scoped_identifier'],
            return_type=d['return_type'],
            umid=d['umid'],
            signature=d['signature'],
            body=d['body'],
            dependency_names=[],
            start_line=d['start_line'],
            parameters=d.get('parameters', [])
        )
        m.description = d.get('description', '')
        m.dependencies = d.get('dependencies', [])
        m.id = d['id']
        m.end_line = d['end_line']
        m.body_hash = d['body_hash']
        
        # Inject the mock file for file path resolution in serialization
        from toaster.core.models import BaseFile
        class MockFile(BaseFile):
            def resolve_dependencies(self): pass
            
        mf = MockFile(ufid=path, imports=[], classes=[])
        mf.source_path = path
        m.file = mf
        
        # Inject mock class for resolution
        from toaster.core.models import BaseClass
        class MockClass(BaseClass):
            def skeletonize(self): pass
        mc = MockClass(ucid=d.get('_class_ucid', ''), signature='', body='', start_line=0, child_classes={}, methods={})
        m.parent_class = mc
        
        return m

    def _create_class(self, d: dict) -> "BaseClass":
        from toaster.languages.java.models import JavaClass
        from toaster.languages.csharp.models import CSharpClass
        
        path = d.get("_file_source_path", "unknown.java")
        class_cls = CSharpClass if path.endswith(".cs") else JavaClass
        
        c = class_cls(
            ucid=d['ucid'],
            signature=d['signature'],
            body=d['body'],
            start_line=d['start_line'],
            child_classes={},
            methods={}
        )
        c.description = d.get('description', '')
        c.constants = d.get('constants', [])
        c.id = d['id']
        c.end_line = d['end_line']
        
        for md in d.get("methods", []):
            md["_file_source_path"] = path
            md["_class_ucid"] = c.ucid
            m = self._create_method(md)
            m.parent_class = c
            c.methods[m.umid] = m
            
        for cd in d.get("child_classes", []):
            cd["_file_source_path"] = path
            child = self._create_class(cd)
            c.child_classes[child.ucid] = child
            
        return c

    def _create_file(self, d: dict) -> "BaseFile":
        from toaster.languages.java.models import JavaFile
        from toaster.languages.csharp.models import CSharpFile
        
        path = d.get("source_path") or d.get("ufid", "")
        file_cls = CSharpFile if path.endswith(".cs") else JavaFile
        
        f = file_cls(
            ufid=d['ufid'],
            imports=d.get('imports', []),
            classes=[]
        )
        f.source_path = path
        f.id = d['id']
        
        for cd in d.get("classes", []):
            cd["_file_source_path"] = path
            child = self._create_class(cd)
            f.classes.append(child)
            
        return f

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
                return self._create_method(self._parse_row(row))
                
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
                return self._create_class(row_dict)
                
            elif id.startswith("F-"):
                row = conn.execute("SELECT * FROM files WHERE id = ?", (id,)).fetchone()
                if not row: return None
                row_dict = self._parse_row(row)
                c_rows = conn.execute("SELECT * FROM classes WHERE file_id = ? AND parent_class_id IS NULL", (id,)).fetchall()
                row_dict["classes"] = [self._parse_row(c) for c in c_rows]
                return self._create_file(row_dict)
                
            return None