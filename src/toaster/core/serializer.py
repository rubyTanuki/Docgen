from typing import List

from toaster.core.models import BaseFile, BaseClass, BaseMethod, BaseEnum


class toast:
    
    @classmethod
    def dump_method(cls, m: BaseMethod) -> str:
        output = f"""
{m.id} @L{m.line} | {m.signature}
// {m.description}"""
        # outbound dependencies
        if m.dependencies:
            output += '\n>' + ', '.join(m.dependencies)
        # dont add outbound for base .toast output
        # if m.inbound_dependencies:
        #     output += '<' + ', '.join(m.inbound_dependencies)
        
        return output
        
    @classmethod
    def dump_class(cls, c: BaseClass) -> str:
        is_enum = isinstance(c, BaseEnum)
        output = f"""
{c.id} | {c.signature} {f"{{{', '.join(c.constants)}}}" if is_enum else ""}
// {c.description}
"""
        if is_enum:
            output += f""
            
        if c.fields:
            output += f"fields: {', '.join(c.fields.keys())}"
        for method in c.methods.values():
            output += cls.dump_method(method)
        for class_obj in c.child_classes.values():
            output += cls.dump_class(class_obj)
        return output
        
        
    @classmethod
    def dump_file(cls, f: BaseFile) -> str:
        output = f"""
{f.id} | {f.ufid}
"""
        if f.imports:
            output += f"imports: {', '.join(f.imports)}"
        for c in f.classes:
            output += cls.dump_class(c)
        return output
    
    @classmethod
    def dump_project(cls, project: BaseParser) -> str:
        return '\n'.join([cls.dump_file(f) for f in project.files])