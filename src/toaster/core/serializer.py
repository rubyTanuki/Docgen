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
    def dump_dict(cls, d: dict, verbosity: Verbosity=Verbosity.SIMPLE) -> str:
        struct_id = d.get("id", "")
        if struct_id.startswith("M-"):
            line_range = f"@L{d.get('start_line')}-{d.get('end_line')}"
            
            parts = []
            if "_file_source_path" in d:
                parts.append(f"/{d['_file_source_path']}")
            if "_class_ucid" in d:
                parts.append(f"{d['_class_ucid']}")
                
            parts.append(f"{struct_id} {line_range} | {d.get('signature')}")
            if verbosity >= Verbosity.SIMPLE:
                desc = d.get('description')
                if desc:
                    parts.append(f"// {desc}")
                deps = d.get('dependencies', [])
                if deps:
                    flat_deps = []
                    for dep in deps:
                        if isinstance(dep, list):
                            flat_deps.append(dep[-1] if len(dep) > 1 else dep[0])
                        else:
                            flat_deps.append(str(dep))
                    parts.append(f"> {', '.join(flat_deps)}")
            if verbosity >= Verbosity.FULL:
                body = d.get("body")
                if body:
                    parts.append(f"```\n{body}\n```")
            return "\n" + "\n".join(parts)
            
        elif struct_id.startswith("C-"):
            output = f"\n{struct_id} | {d.get('signature')}"
            if verbosity > Verbosity.MINIMAL:
                constants = d.get("constants", [])
                if constants:
                    output += f" {{{', '.join(constants)}}}"
                desc = d.get('description')
                if desc:
                    output += f"\n// {desc}"
            return output
            
        elif struct_id.startswith("F-"):
            output = f"\n{struct_id} | {d.get('ufid')}\n"
            imports = d.get('imports', [])
            if imports:
                output += f"imports: {', '.join(imports)}"
            return output
            
        return json.dumps(d, indent=4)
    
    @classmethod
    def dump_method(cls, m: BaseMethod, verbosity: Verbosity = Verbosity.SIMPLE) -> str:
        line_range = f"@L{m.start_line}-{m.end_line}"
        
        parts = [f"{m.id} {line_range} | {m.signature}"]

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
    
