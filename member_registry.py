from collections import defaultdict

class MemberRegistry:
    # registry of all methods, indexed by 
    methods = defaultdict(list)
    methods_by_name = defaultdict(list)
    
    
    def add_method(method: "Method"):
        MemberRegistry.methods[method.name].append(method)
        MemberRegistry.methods_by_name[method.identifier].append(method)
        
    def resolve_method(identifier: str) -> list["Method"]:
        return MemberRegistry.methods[identifier]
    
    def resolve_method_by_name(name: str) -> list["Method"]:
        return MemberRegistry.methods_by_name[name]