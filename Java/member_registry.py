from collections import defaultdict

class MemberRegistry:
    methods = {}
    methods_by_name = defaultdict(list)
    
    
    def add_method(method):
        MemberRegistry.methods[method.name] = method
        MemberRegistry.methods_by_name[method.identifier].append(method)
        
    def resolve_method(identifier: str):
        return MemberRegistry.methods[identifier]
    
    def resolve_method(name: str):
        return MemberRegistry.methods_by_name[name]