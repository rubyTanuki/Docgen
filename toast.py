from typing import List


class toast:
    
    @classmethod
    def dump_method(cls, m: BaseMethod) -> str:
        output = f"""
M{m.id} @L{m.line} | {m.signature}
// {m.description}
"""
        # outbound dependencies
        if m.dependencies:
            output += '>' + ', '.join(m.dependencies)
        
        return output
        
    @classmethod
    def dump_class(cls, c: BaseClass) -> str:
        output = f"""
C{c.id}: {c.signature}
// {c.description}
fields: {', '.join(c.fields.keys())}

"""
        for method in c.methods.values():
            output += cls.dump_method(method)
        return output
        
    @classmethod
    def dump_file(cls, f: BaseFile) -> str:
        output = f"""
F{f.id}: {f.ufid}
imports: {', '.join(f.imports)}
"""
        for c in f.classes:
            output += cls.dump_class(c)
        return output
    
    @classmethod
    def dump_project(cls, project: BaseParser) -> str:
        return '\n'.join([cls.dump_file(f) for f in project.files])