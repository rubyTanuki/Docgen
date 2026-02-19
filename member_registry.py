from collections import defaultdict
from typing import List, Dict, Optional

class MemberRegistry:
    # "com.pkg.Class#method(int)" -> Method
    map_umid: Dict[str, "JavaMethod"] = {}
    
    # "com.pkg.Class.method" -> [Method(int), Method(str)]
    map_scoped: Dict[str, List["JavaMethod"]] = defaultdict(list)
    
    # "method" -> [Method(ClassA), Method(ClassB)]
    map_short: Dict[str, List["JavaMethod"]] = defaultdict(list)
    
    
    @classmethod
    def add_method(cls, method):
        cls.map_umid[method.umid] = method
        
        cls.map_scoped[method.scoped_identifier].append(method)
        
        cls.map_short[method.identifier].append(method)