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
    def __init__(self, use_cache: bool = True, db: SQLiteCache = None):
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
    
    def add_struct(self, struct: BaseStruct):
        """ Adds a struct to the in-memory cache """
        self.uid_map[struct.uid] = struct
        self.id_map[struct.id] = struct
        
    def load_subtree(self, path: Path):
        logger.info(f"Loading subtree {str(path)}")
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # pull and hydrate structs
            cursor.execute("SELECT * FROM structs WHERE uid LIKE ? || '%'", (str(path.resolve()),))
            node_rows = cursor.fetchall()
            node_ids = [row['id'] for row in node_rows]
            
            for row in node_rows:
                struct_data = dict(row)
                
                if struct_data.get('imports', None):
                    struct_data['imports'] = json.loads(struct_data['imports'])
                
                builder = BaseBuilder(self)
                struct_type = struct_data['type']
                logger.debug(f"{struct_type=}")
                instance = builder.with_type(struct_type=struct_data['type']).from_dict(struct_data)
                self.add_struct(instance)
            
            logger.info(f"Found {len(node_rows)} structs in subtree {str(path.resolve())}")
            
            
            
            if not node_ids:
                return
            
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
            
            logger.info(f"Found {len(edge_rows)} edges in subtree {path.resolve()}")
            
            for source_id, target_id, edge_type in edge_rows:
                source_obj = self.get_struct_by_id(source_id)
                target_obj = self.get_struct_by_id(target_id)
                
                if not source_obj or not target_obj:
                    continue
                
                target_obj.add_child(source_obj)
    
    def get_struct_by_uid(self, uid: str) -> Optional["BaseStruct"]:
        # Check memory cache first and return early if found
        if uid in self.uid_map:
            return self.uid_map[uid]

        if not self.use_cache or not self.db:
            return None
        
        from toaster.core.builder import BaseBuilder
        import json
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # fetch struct and its children via prefix search
            cursor.execute("SELECT * FROM structs WHERE uid LIKE ?", (f"{uid}%",))
            node_rows = cursor.fetchall()
            
            if not node_rows:
                return None
                
            node_ids = []
            
            for row in node_rows:
                struct_data = dict(row)
                node_ids.append(struct_data['id'])
                
                # Skip hydrating if it somehow already exists in memory
                if struct_data['uid'] not in self.uid_map:
                    if struct_data.get('imports', None):
                        struct_data['imports'] = json.loads(struct_data['imports'])
                    
                    builder = BaseBuilder(self)
                    instance = builder.with_type(struct_type=struct_data['type']).from_dict(struct_data)
                    self.add_struct(instance)
            
            # Fetch and connect edges
            if node_ids:
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
                
                for source_id, target_id, edge_type in edge_rows:
                    source_obj = self.id_map.get(source_id)
                    target_obj = self.id_map.get(target_id)
                    
                    if not source_obj or not target_obj:
                        continue
                    
                    target_obj.add_child(source_obj)
                    
        return self.uid_map.get(uid)

    
    def get_struct_by_id(self, id: str) -> Optional["BaseStruct"]:
        # Check memory cache first and return early if found
        if hasattr(self, 'id_map') and id in self.id_map:
            return self.id_map[id]
            
        if not self.use_cache or not self.db:
            return None
        
        # Fetch UID from db for prefix search
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT uid FROM structs WHERE id = ?", (id,)).fetchone()
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
    
    def save_to_cache(self):
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