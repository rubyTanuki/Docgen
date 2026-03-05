from collections import defaultdict
from typing import List, Dict, Optional

class MemberRegistry:
    def __init__(self):
        # "com.pkg.Class#method(int)" -> Method
        self.map_umid: Dict[str, "BaseMethod"] = {}
        
        # "com.pkg.Class.method" -> [Method(int), Method(str)]
        self.map_scoped: Dict[str, List["BaseMethod"]] = defaultdict(list)
        
        # "method" -> [Method(ClassA), Method(ClassB)]
        self.map_short: Dict[str, List["BaseMethod"]] = defaultdict(list)
        
        # "com.pkg.Class" -> Class
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
    
    def get_method_cache(self):
        return { m.umid: {
            "hash": m.body_hash,
            "description": m.description
        } for m in self.map_umid.values()}
    
    def get_class_cache(self):
        return {c.ucid: {
            "description": c.description
        } for c in self.map_class.values()}
    
    def get_cache(self):
        return {
            'classes': self.get_class_cache(),
            'methods': self.get_method_cache()
        }
    
    def load_cache(self, cache: Dict[str, Dict[str, str]]):
        
        # load methods
        method_cache = cache.get('methods')
        for method in self.map_umid.values():
            cached_data = method_cache.get(method.umid)
            if cached_data and cached_data["hash"] == method.body_hash:
                method.description = cached_data["description"]
            else:
                method.description = ""
        
        # load classes
        class_cache = cache.get('classes')
        for c in self.map_class.values():
            cached_data = class_cache.get(c.ucid)
            if cached_data and cached_data.get('description'):
                c.description = cached_data['description']
                
    def get_struct_by_id(self, id: str) -> Optional["BaseStruct"]:
        return self.map_id.get(id, None)