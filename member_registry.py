from collections import defaultdict
from typing import List, Dict, Optional

class MemberRegistry:
    # "com.pkg.Class#method(int)" -> Method
    map_umid: Dict[str, "JavaMethod"] = {}
    
    # "com.pkg.Class.method" -> [Method(int), Method(str)]
    map_scoped: Dict[str, List["JavaMethod"]] = defaultdict(list)
    
    # "method" -> [Method(ClassA), Method(ClassB)]
    map_short: Dict[str, List["JavaMethod"]] = defaultdict(list)
    
    # "com.pkg.Class" -> Class
    map_class = {}
    
    method_cache: Dict[str, Dict[str, str]] = {}
    
    class_cache: Dict[str, Dict[str, str]] = {}
    
    
    @classmethod
    def add_method(cls, method):
        cls.map_umid[method.umid] = method
        
        cls.map_scoped[method.scoped_identifier].append(method)
        
        cls.map_short[method.identifier].append(method)
        
    @classmethod
    def add_class(cls, class_obj):
        cls.map_class[class_obj.ucid] = class_obj
        
    @classmethod
    def get_method_cache(cls):
        return { m.umid: {
            "hash": m.body_hash,
            "description": m.description
        } for m in cls.map_umid.values()}
        
    @classmethod
    def get_class_cache(cls):
        return {c.ucid: {
            "description": c.description
        } for c in cls.map_class.values()}
    
    @classmethod
    def get_cache(cls):
        return {
            'classes': cls.get_class_cache(),
            'methods': cls.get_method_cache()
        }
    
    @classmethod
    def load_cache(cls, cache: Dict[str, Dict[str, str]]):
        # assert cache['methods']
        # assert cache['classes']
        
        # load methods
        cls.method_cache = cache.get('methods')
        for method in cls.map_umid.values():
            cached_data = cache['methods'].get(method.umid)
            if cached_data and cached_data["hash"] == method.body_hash:
                method.description = cached_data["description"]
            else:
                method.description = ""
        
        # load classes
        cls.class_cache = cache.get('classes')
        for c in cls.map_class.values():
            cached_data = cls.class_cache.get(c.ucid)
            if cached_data and cached_data.get('description'):
                c.description = cached_data['description']
                
                