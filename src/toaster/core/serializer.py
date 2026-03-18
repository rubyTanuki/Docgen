from typing import List

from toaster.core.models import BaseFile, BaseClass, BaseMethod

from enum import IntEnum

class Verbosity(IntEnum):
    SKELETON = 1
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
        parts.append(f"{m.id} {line_range} | {m.signature}")
        parts.append(f"// {m.description}")

        if verbosity >= Verbosity.SIMPLE:
            if m.parent_class and m.parent_class.ucid:
                parts.insert(0, f"{m.parent_class.ucid}")
            if m.file and m.file.source_path:
                parts.insert(0, f"/{m.file.source_path}")
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

        return "\n".join(parts)
        
    @classmethod
    def dump_class(cls, c: BaseClass, verbosity: Verbosity=Verbosity.SIMPLE) -> str:
        is_enum = len(c.constants)>0
        
        parts = []
        
        header_str = f"{c.id} | {c.signature}"
        # append enum constants
        if is_enum:
            header_str += f" {{{', '.join(c.constants)}}}"
        parts.append(header_str)
        
        # append description
        parts.append(f"// {c.description}")
        
        if verbosity > Verbosity.SKELETON:
            if c.file and c.file.ufid:
                parts.insert(0, f"/{c.file.ufid}")

            # append fields
            if c.fields:
                parts.append(f"fields: {', '.join(c.fields.keys())}")
                
            # append methods
            if c.methods:
                parts.append("\n" + "\n".join([cls.dump_method(m, Verbosity.SKELETON) for m in c.methods.values()]))
            # append child classes
            for class_obj in c.child_classes.values():
                parts.append(cls.dump_class(class_obj, verbosity))
        return "\n".join(parts)
        
        
    @classmethod
    def dump_file(cls, f: BaseFile, verbosity: Verbosity=Verbosity.SIMPLE) -> str:
        parts = []
        
        parts.append(f"{f.id} | {f.ufid}")
        if verbosity > Verbosity.SKELETON:
            if f.imports:
                parts.append(f"imports: {', '.join(f.imports)}")
                
        for c in f.classes:
            parts.append(cls.dump_class(c, verbosity))
        return "\n".join(parts)
    
    @classmethod
    def dump_project(cls, project: BaseParser, verbosity: Verbosity=Verbosity.SIMPLE) -> str:
        return '\n\n'.join([cls.dump_file(f, verbosity) for f in project.files])
    
    @classmethod
    def dump_files(cls, files: list[BaseFile], verbosity: Verbosity=Verbosity.SIMPLE)->str:
        return '\n' + '\n\n'.join([cls.dump_file(f, verbosity) for f in files])
    
