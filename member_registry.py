from collections import defaultdict
from typing import List, Dict, Optional

class MemberRegistry:
    # "com.pkg.Class#method(int)" -> Method
    map_umid: Dict[str, "JavaMethod"] = {}
    
    # "com.pkg.Class.method" -> [Method(int), Method(str)]
    map_scoped: Dict[str, List["JavaMethod"]] = defaultdict(list)
    
    # "method" -> [Method(ClassA), Method(ClassB)]
    map_short: Dict[str, List["JavaMethod"]] = defaultdict(list)
    
    method_cache: Dict[str, Dict[str, str]] = {}
    
    
    @classmethod
    def add_method(cls, method):
        cls.map_umid[method.umid] = method
        
        cls.map_scoped[method.scoped_identifier].append(method)
        
        cls.map_short[method.identifier].append(method)
        
    @classmethod
    def get_method_cache(cls):
        return { m.umid: {
            "hash": m.body_hash,
            "description": m.description
        } for m in cls.map_umid.values()}
    
    @classmethod
    def load_cache(cls, cache: Dict[str, Dict[str, str]]):
        cls.method_cache = cache
        for method in cls.map_umid.values():
            cached_data = cache.get(method.umid)
            if cached_data and cached_data["hash"] == method.body_hash:
                method.description = cached_data["description"]
            else:
                method.description = ""
                
                