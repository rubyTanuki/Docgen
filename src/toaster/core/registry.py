from collections import defaultdict
from typing import List, Dict, Optional, TYPE_CHECKING
from pathlib import Path
from toaster.core.models import BaseFile, BaseClass, BaseMethod, BaseField
from toaster.core.db import SQLiteCache

if TYPE_CHECKING:
    from toaster.core.models import BaseStruct, BaseCodeStruct

class Registry:
    def __init__(self, use_cache: bool = True, db: SQLiteCache = None):
        self.use_cache = use_cache
        self.uid_map: Dict[str, BaseStruct] = {}
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
    
    def get_struct_by_uid(self, uid: str) -> List[BaseStruct]:
        # check memory cache first and return early if found
        if uid in self.uid_map:
            return self.uid_map[uid]

        if not self.use_cache or not self.db:
            return []
        
        from toaster.core.builder import BaseBuilder
        
        # get sqlite connection
        struct_json = {}
        with self.db.get_connection() as conn:
            # SELECT * FROM structs WHERE uid = uid
            row = conn.execute("SELECT * FROM structs WHERE uid = ?", (uid,)).fetchone()
            if not row:
                return []
            struct_json = dict(row)
        
        builder = BaseBuilder(self)
        # Hydrate the returned struct into its in-memory representation
        struct = builder.with_type(struct_json["type"]).from_dict(struct_json)
        # add the hydrated struct to the memory cache for faster future retrieval
        self.add_struct(struct)
        return struct
    
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
        
        for node in self.uid_map.values():
            data_dict = node.to_dict()
            data_json = node.to_json()
            
            # Use the tuple of keys as the group identifier
            column_footprint = tuple(data_dict.keys())
            grouped_nodes[column_footprint].append(data_json)
            
            all_edges.update(node.edges)
            
        with self.db.get_connection() as conn:
            
            # Iterate through each unique column footprint and execute its batch
            for columns_tuple, dict_list in grouped_nodes.items():
                
                columns = ", ".join(columns_tuple)
                placeholders = ", ".join(["?"] * len(columns_tuple))
                node_sql = f"INSERT OR REPLACE INTO structs ({columns}) VALUES ({placeholders})"
                
                node_values = [
                    tuple((n) for col in columns_tuple)
                    for n in dict_list
                ]
                
                conn.executemany(node_sql, node_values)
            
            # delete all existing edges with self as source
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