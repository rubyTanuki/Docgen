from typing import List

from toaster.core.models import BaseFile, BaseClass, BaseMethod

from enum import IntEnum

class Verbosity(IntEnum):
    MINIMAL = 1
    SIMPLE = 2
    VERBOSE = 3
    FULL = 4

class toast:
    
    @classmethod
    def dumps(cls, obj: "BaseStruct", verbosity: Verbosity=Verbosity.SIMPLE) -> str:
        match obj:
            case BaseFile():
                return cls.dump_file(obj, verbosity=verbosity)
            case BaseClass():
                return cls.dump_class(obj, verbosity=verbosity)
            case BaseMethod():
                return cls.dump_method(obj, verbosity=verbosity)
            case _:
                raise TypeError(f"Unsupported type: {type(obj)}")


    
    @classmethod
    def dump_method(cls, m: BaseMethod, verbosity: Verbosity = Verbosity.SIMPLE) -> str:
        line_range = f"@L{m.start_line}-{m.end_line}"
        
        parts = []
        if m.file and m.file.source_path:
            parts.append(f"/{m.file.source_path}")
        if m.parent_class and m.parent_class.ucid:
            parts.append(f"{m.parent_class.ucid}")
            
        parts.append(f"{m.id} {line_range} | {m.signature}")

        if verbosity >= Verbosity.SIMPLE:
            parts.append(f"// {m.description}")
            if m.dependencies:
                parts.append(f"> {', '.join(m.dependencies)}")

        if verbosity >= Verbosity.VERBOSE:
            if m.inbound_dependencies:
                parts.append(f"< {', '.join(m.inbound_dependencies)}")
            parts.append(f"# impact score: {m.impact_score}")

        if verbosity >= Verbosity.FULL:
            if m.unresolved_dependencies:
                parts.append(f"# unresolved dependencies: {', '.join(m.unresolved_dependencies)}")
            
            parts.append(f"java ```\n{m.body}\n```")

        return "\n" + "\n".join(parts)
        
    @classmethod
    def dump_class(cls, c: BaseClass, verbosity: Verbosity=Verbosity.SIMPLE) -> str:
        is_enum = len(c.constants)>0
        output = f"\n{c.id} | {c.signature}"
        if verbosity > Verbosity.MINIMAL:
            # append enum constants
            if is_enum:
                output += f" {{{', '.join(c.constants)}}}"

            # append description
            output += f"\n// {c.description}"

            # append fields
            if c.fields:
                output += f"fields: {', '.join(c.fields.keys())}"
                
            # append methods
            for method in c.methods.values():
                output += cls.dump_method(method, verbosity)
            # append child classes
            for class_obj in c.child_classes.values():
                output += cls.dump_class(class_obj, verbosity)
        return output
        
        
    @classmethod
    def dump_file(cls, f: BaseFile, verbosity: Verbosity=Verbosity.SIMPLE) -> str:
        output = f"""
{f.id} | {f.ufid}
"""
        if f.imports:
            output += f"imports: {', '.join(f.imports)}"
        for c in f.classes:
            output += cls.dump_class(c, verbosity)
        return output
    
    @classmethod
    def dump_project(cls, project: BaseParser, verbosity: Verbosity=Verbosity.SIMPLE) -> str:
        return '\n'.join([cls.dump_file(f, verbosity) for f in project.files])
    
