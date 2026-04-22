from collections import defaultdict
from typing import List, Dict, Optional, TYPE_CHECKING
from pathlib import Path
from toaster.core.models import BaseFile, BaseClass, BaseMethod, BaseField
from toaster.core.db import SQLiteCache
from toaster.core.builder import BaseBuilder

import json
from loguru import logger

if TYPE_CHECKING:
    from toaster.core.models import BaseStruct, BaseCodeStruct

class Registry:
    def __init__(self, use_cache: bool = True, db: SQLiteCache = None, project_path: Path = None):
        self.project_path = project_path
        self.use_cache = use_cache
        self.uid_map: Dict[str, BaseStruct] = {}
        self.id_map: Dict[str, BaseStruct] = {}
        self.root: Optional[BaseStruct] = None
        self.db = db
    
    @property
    def files(self) -> List[BaseFile]:
        return [x for x in self.uid_map.values() if isinstance(x, BaseFile)]
    
    @property
    def classes(self) -> List[BaseClass]:
        return [x for x in self.uid_map.values() if isinstance(x, BaseClass)]
    
    @property
    def methods(self) -> List[BaseMethod]:
        return [x for x in self.uid_map.values() if isinstance(x, BaseMethod)]
    
    @property
    def fields(self) -> List[BaseField]:
        return [x for x in self.uid_map.values() if isinstance(x, BaseField)]
    
    def relative_to_project(self, path: Path) -> Path:
        if self.project_path:
            return path.resolve().relative_to(self.project_path.resolve())
        return path
    
    def add_struct(self, struct: BaseStruct):
        """ Adds a struct to the in-memory cache """
        self.uid_map[struct.uid] = struct
        self.id_map[struct.id] = struct
        
    def resolve_methods(self, name: str, arity: int, parent_name: Optional[str] = None):
        if parent_name:
            return [x for x in self.methods if x.name == name and x.arity == arity and x.parent.name == parent_name]
        return [x for x in self.methods if x.name == name and x.arity == arity]
    
    def load_filepath(self, path: Path):
        logger.debug(f"Loading subtree {str(path)}")
        path_str = str(self.relative_to_project(path))
        resolved_path_str = str(path.resolve())
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # pull and hydrate structs
            if path_str != ".":
                cursor.execute("SELECT * FROM structs WHERE path LIKE ? || '%'", (resolved_path_str,))
            else:
                cursor.execute("SELECT * FROM structs")
                
            node_rows = cursor.fetchall()
            node_ids = [str(row['id']) for row in node_rows]
            
            for row in node_rows:
                struct_data = dict(row)
                
                if struct_data.get('imports', None):
                    struct_data['imports'] = json.loads(struct_data['imports'])
                
                builder = BaseBuilder(self)
                struct_type = struct_data['type']
                instance = builder.with_type(struct_type=struct_type).from_dict(struct_data)
                
                if instance:
                    self.add_struct(instance)
            
            logger.debug(f"Found {len(node_rows)} structs in subtree {path_str}")
            
            if not node_ids:
                return None
            
            placeholders = ",".join(["?"] * len(node_ids))
            
            if path_str == ".":
                sql = f"""
                    SELECT source_id, target_id, edge_type 
                    FROM edges
                    WHERE edge_type = 'is_child_of'
                """
                cursor.execute(sql)
            else:
                sql = f"""
                    SELECT source_id, target_id, edge_type 
                    FROM edges 
                    WHERE (source_id IN ({placeholders}) 
                    OR target_id IN ({placeholders}))
                    AND edge_type = 'is_child_of'
                """
                params = node_ids + node_ids
                cursor.execute(sql, params)
            
            edge_rows = cursor.fetchall()
            
            logger.debug(f"Found {len(edge_rows)} edges in subtree {path_str}")
            
            
            for source_id, target_id, edge_type in edge_rows:
                source_obj = self.id_map.get(str(source_id))
                target_obj = self.id_map.get(str(target_id))
                
                if not source_obj or not target_obj:
                    logger.warning(f"Edge references missing struct. Source ID: {source_id}, Target ID: {target_id}, Edge Type: {edge_type}")
                    continue
                
                target_obj.add_child(source_obj)
        
        self.root = self.get_struct_by_uid(path_str)
                
        logger.debug(f"Loaded subtree {path_str} with root {self.root}")
        
        return self.root
    
    def get_struct_by_uid(self, uid: str) -> Optional["BaseStruct"]:
        logger.debug(f"Attempting to retrieve struct and its children with UID {uid} from registry")
        
        # Check memory cache first
        if uid in self.uid_map:
            logger.debug(f"Cache hit for UID {uid}, returning memory object")
            return self.uid_map[uid]

        if not self.use_cache or not self.db:
            logger.debug(f"Cache miss for UID {uid}, but no DB provided or caching disabled, returning None")
            return None
        
        from toaster.core.builder import BaseBuilder
        import json
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Target exact match alongside delimiter-specific prefix matches 
            # to retrieve the target struct and all hierarchical descendants (directories or code structs)
            if uid != ".":
                cursor.execute(
                    "SELECT * FROM structs WHERE uid = ? OR uid LIKE ? OR uid LIKE ?", 
                    (uid, f"{uid}%", f"{uid}#%")
                )
            else:
                cursor.execute("SELECT * FROM structs")
            node_rows = cursor.fetchall()
            
            if not node_rows:
                logger.debug(f"No structs found in DB matching UID {uid}")
                return None
                
            node_ids = [str(row['id']) for row in node_rows]
            target_id = None
            
            for row in node_rows:
                struct_data = dict(row)
                current_id = str(struct_data['id'])
                
                # Isolate the requested target struct ID for the final return
                if struct_data['uid'] == uid:
                    target_id = current_id
                
                if current_id not in self.id_map:
                    if struct_data.get('imports', None):
                        struct_data['imports'] = json.loads(struct_data['imports'])
                    
                    builder = BaseBuilder(self)
                    struct_type = struct_data['type']
                    instance = builder.with_type(struct_type=struct_type).from_dict(struct_data)
                    
                    if instance:
                        self.add_struct(instance)
                        # logger.debug(f"Created instance for struct with DB UID {struct_data['uid']} and type {struct_type}")
                    else:
                        logger.warning(f"Builder failed to create instance for struct with UID {struct_data['uid']} and type {struct_type}")
            
            if not node_ids:
                return None
            
            # Fetch and connect edges for the loaded subset
            placeholders = ",".join(["?"] * len(node_ids))
            sql = f"""
                SELECT source_id, target_id, edge_type 
                FROM edges 
                WHERE (source_id IN ({placeholders}) 
                OR target_id IN ({placeholders}))
                AND edge_type = 'is_child_of'
            """
            
            params = node_ids + node_ids
            cursor.execute(sql, params)
            edge_rows = cursor.fetchall()
            
            for _source_id, _target_id, edge_type in edge_rows:
                source_obj = self.id_map.get(str(_source_id))
                target_obj = self.id_map.get(str(_target_id))
                
                if not source_obj or not target_obj:
                    continue
                
                target_obj.add_child(source_obj)
                    
        struct = self.id_map.get(target_id) if target_id else None
        
        if struct is None:
            logger.warning(f"Struct with DB UID {uid} was not found in memory cache after DB retrieval. Target ID: {target_id}")
        return struct


    def get_struct_by_id(self, id: str) -> Optional["BaseStruct"]:
        id_str = str(id)
        
        # Check memory cache first
        if hasattr(self, 'id_map') and id_str in self.id_map:
            return self.id_map[id_str]
            
        if not self.use_cache or not self.db:
            return None
        
        # Fetch UID from db to execute localized subtree retrieval
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT uid FROM structs WHERE id = ?", (id_str,)).fetchone()
            logger.debug(f"Queried DB for struct with id {id_str}, got uid: {row[0]}")
            if not row:
                return None
            
            target_uid = row[0]
            
        return self.get_struct_by_uid(target_uid)
    
    def is_stale(self, struct: BaseCodeStruct | str) -> bool:
        if not self.db:
            raise RuntimeError("Cannot check for stale structs if SqLiteCache not provided.")
        if isinstance(struct, str):
            if struct not in self.uid_map:
                raise KeyError(f"Could not find struct with uid {struct}")
            struct = self.uid_map[struct]
            
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT diff_hash FROM structs WHERE uid = ?", (struct.uid,)).fetchone()
            if not row or row[0] != struct.diff_hash:
                return True
            return False
        
    def update_cached_description(self, struct: BaseStruct | str):
        if not self.db:
            raise RuntimeError("Cannot check for stale structs if SqLiteCache not provided.")
        if isinstance(struct, str):
            if struct not in self.uid_map:
                raise KeyError(f"Could not find struct with uid {struct}")
            struct = self.uid_map[struct]
        
        with self.db.get_connection() as conn:
            conn.execute("UPDATE structs SET description = ? WHERE uid = ?", (struct.description, struct.uid))
            conn.commit()
        

    def save_struct_to_cache(self, struct: BaseStruct | str):
        """ Saves a struct to the SQLite cache """
        if not self.db:
            raise RuntimeError("Cannot save to cache if SqLiteCache not provided.")
        if isinstance(struct, str):
            if struct not in self.uid_map:
                raise KeyError(f"Could not find struct with uid {struct}")
            struct = self.uid_map[struct]
        
        data = struct.to_dict()
        
        target_uid = data.pop("uid") 
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        node_sql = f"UPDATE structs SET {set_clause} WHERE uid = ?"
        node_params = list(data.values()) + [target_uid]
        
        edges = list(struct.edges)
            
        with self.db.get_connection() as conn:
            conn.execute(node_sql, node_params)
            
            # Clear all existing edges touching this node to prevent ghosts
            conn.execute("DELETE FROM edges WHERE source_id = ?", (struct.id,))
            
            # Bulk insert fresh edges
            if edges:
                conn.executemany("INSERT INTO edges (source_id, target_id, edge_type) VALUES (?, ?, ?)", edges)
            conn.commit()
    
    def save_to_cache(self, stale: bool = False):
        """Saves the entire AST to the SQLite cache."""
        if not self.db:
            raise RuntimeError("Cannot save to cache if SqLiteCache not provided.")
        
        parsed_ids = [(node.id,) for node in self.uid_map.values()]
        grouped_nodes = defaultdict(list)
        all_edges = set()
        
        def serialize_for_db(value):
            if isinstance(value, (dict, list, tuple, set)):
                if isinstance(value, set):
                    value = list(value)
                return json.dumps(value)
            return value
        
        for node in self.uid_map.values():
            data_dict = node.to_dict()
            if stale and data_dict.get("description", None):
                data_dict["description"] = f"[STALE] {data_dict['description']}"
            
            # tuple of keys as the group identifier
            column_footprint = tuple(data_dict.keys())
            
            grouped_nodes[column_footprint].append(data_dict) 
            all_edges.update(node.edges)
            
        with self.db.get_connection() as conn:
            for columns_tuple, dict_list in grouped_nodes.items():
                
                columns = ", ".join(columns_tuple)
                placeholders = ", ".join(["?"] * len(columns_tuple))
                node_sql = f"INSERT OR REPLACE INTO structs ({columns}) VALUES ({placeholders})"
                
                # Fetching the specific value for each column from the dictionary
                node_values = [
                    tuple(serialize_for_db(n.get(col)) for col in columns_tuple)
                    for n in dict_list
                ]
                
                conn.executemany(node_sql, node_values)
            
            conn.executemany(
                "DELETE FROM edges WHERE source_id = ?", 
                parsed_ids
            )
            
            if all_edges:
                conn.executemany(
                    "INSERT INTO edges (source_id, target_id, edge_type) VALUES (?, ?, ?)",
                    list(all_edges)
                )
            conn.commit()