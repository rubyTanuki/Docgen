from typing import List

from toaster.core.models import BaseFile, BaseClass, BaseMethod

from enum import IntEnum

import textwrap
from collections import defaultdict

_INDENT_TAB = "      "

_LINE_WRAP_WIDTH = 90

class Verbosity(IntEnum):
    HEADER = 0
    SKELETON = 1
    SIMPLE = 2
    VERBOSE = 3
    FULL = 4

class toast:
    
    @classmethod
    def is_serializable(cls, obj) -> bool:
        return isinstance(obj, (BaseFile, BaseClass, BaseMethod))
    
    @classmethod
    def dumps(cls, obj: "BaseStruct", verbosity: Verbosity=Verbosity.SIMPLE, include_body: bool = False, pretty: bool = True) -> str:
        match obj:
            case BaseFile():
                return cls.dump_file(obj, verbosity=verbosity, include_body=include_body, pretty=pretty)
            case BaseClass():
                return cls.dump_class(obj, verbosity=verbosity, include_body=include_body, pretty=pretty)
            case BaseMethod():
                return cls.dump_method(obj, verbosity=verbosity, include_body=include_body, pretty=pretty)
            case _:
                raise TypeError(f"Unsupported type: {type(obj)}")
    
    @classmethod
    def dump_method(
        cls, 
        m: BaseMethod, 
        verbosity: Verbosity = Verbosity.SIMPLE, 
        indent: int = 0, 
        include_body: bool = False,
        pretty: bool = True
    ) -> str:
        if verbosity < 0: return "" # AST Tree recursion base case
        
        max_lines = verbosity + 1
        if verbosity == Verbosity.FULL:
            max_lines = 10000
        
        indent_str = _INDENT_TAB*indent if pretty else ""
        line_range = f"@L{m.start_line}-{m.end_line}"
        parts = []
        
        # HEADER
        parts.append(f"{m.id} {line_range} | {m.signature}")
        
        # SKELETON
        if verbosity >= Verbosity.SKELETON:
            if pretty:
                parts.append(textwrap.fill(f"{m.description}", width=_LINE_WRAP_WIDTH-len(indent_str), initial_indent="// ", subsequent_indent="   ", max_lines=max_lines, placeholder="..."))
            else:
                parts.append(f"// {m.description}")

        # SIMPLE
        if verbosity >= Verbosity.SIMPLE:
            if m.dependencies:
                if pretty:
                    parts.append(textwrap.fill(f"{', '.join(m.dependencies)}", width=_LINE_WRAP_WIDTH-len(indent_str), initial_indent=">  ", subsequent_indent="   ", max_lines=max_lines, placeholder="..."))
                else:
                    parts.append(f"> {', '.join(m.dependencies)}")

        # VERBOSE
        if verbosity >= Verbosity.VERBOSE:
            if m.parent_class and m.parent_class.ucid:
                parts.insert(0, f"{m.parent_class.ucid}")
            if m.file and m.file.source_path:
                parts.insert(0, f"/{m.file.source_path}")
            if m.inbound_dependencies:
                if pretty:
                    parts.append(textwrap.fill(f"{', '.join(m.inbound_dependencies)}", width=_LINE_WRAP_WIDTH-len(indent_str), initial_indent="<  ", subsequent_indent="   "))
                else:
                    parts.append(f"< {', '.join(m.inbound_dependencies)}")
            parts.append(f"# impact score: {m.impact_score}")

        # FULL
        if verbosity >= Verbosity.FULL:
            if m.unresolved_dependencies:
                parts.append(f"# unresolved dependencies: {', '.join(m.unresolved_dependencies)}")

        # INCLUDE BODY
        if include_body and m.body:
            parts.append(f"```\n{m.body}\n```")
        
        return textwrap.indent(f"\n".join(parts), indent_str)
        
    @classmethod
    def dump_class(
        cls, c: BaseClass, 
        verbosity: Verbosity=Verbosity.SIMPLE, 
        indent: int = 0, 
        include_body: bool = False,
        pretty: bool = True
        ) -> str:
        is_enum = len(c.constants)>0
        indent_str = _INDENT_TAB*indent
        
        parts = []
        
        max_lines = verbosity + 1
        if verbosity == Verbosity.FULL:
            max_lines = 10000
            
        
        # HEADER
        header_str = f"{c.id} | {c.signature}"
        if is_enum:
            header_str += f" {{{', '.join(c.constants)}}}"
        parts.append(header_str)
        
        # SKELETON
        if verbosity >= Verbosity.SKELETON:
            if pretty:
                parts.append(textwrap.fill(f"{c.description}", width=_LINE_WRAP_WIDTH-len(indent_str), initial_indent="// ", subsequent_indent="   ", max_lines=max_lines, placeholder="..."))
            else:
                parts.append(f"// {c.description}")
        
        # SIMPLE
        if verbosity >= Verbosity.SIMPLE:
            # FIELDS
            if c.fields:
                grouped_fields = defaultdict(list)
                for f in c.fields.values():
                    grouped_fields[f.field_type].append(f.name)
                field_groups = [f"{ftype} {', '.join(names)}" for ftype, names in grouped_fields.items()]
                fields_str = '; '.join(field_groups)
                
                if pretty:
                    parts.append(textwrap.fill(fields_str, width=_LINE_WRAP_WIDTH-len(indent_str), initial_indent="fields:\n   ", subsequent_indent="   ", max_lines=max_lines, placeholder="..."))
                else:
                    parts.append(f"f: {fields_str}")
                
            # METHODS
            if c.methods:
                sorted_methods = sorted(c.methods.values(), key=lambda m: m.impact_score, reverse=True)
                n = 5
                top_methods = sorted_methods[:n]
                rest_methods = sorted_methods[n:]
                
                top_method_strings = []
                rest_method_strings = []
                
                for m in top_methods:
                    top_method_strings.append("\n" + cls.dump_method(m, verbosity=max(0, verbosity-1), indent=indent + 1, pretty=pretty))
                
                for m in rest_methods:
                    rest_method_strings.append(cls.dump_method(m, verbosity=Verbosity.HEADER, indent=indent + 1, pretty=pretty))
                    
                method_str = "methods:\n" + "\n".join(top_method_strings)
                if rest_method_strings:
                    method_str += "\n\n" + "\n".join(rest_method_strings)
                parts.append(method_str)
            # for class_obj in c.child_classes.values():
            #     parts.append(cls.dump_class(class_obj, max(verbosity-1, Verbosity.SKELETON), indent=indent+1))
        
        # VERBOSE
        if verbosity >= Verbosity.VERBOSE:
            if c.file and c.file.ufid:
                parts.insert(0, f"/{c.file.ufid}")
        
        # INCLUDE BODY
        if include_body and c.body:
            parts.append(f"```\n{c.body}\n```")
        

        return textwrap.indent("\n".join(parts), indent_str)
        
        
    @classmethod
    def dump_file(cls, f: BaseFile, verbosity: Verbosity=Verbosity.SIMPLE, indent: int = 0, include_body: bool = False, pretty: bool = True) -> str:
        parts = []
        indent_str = _INDENT_TAB*indent
        
        max_lines = verbosity + 1
        if verbosity == Verbosity.FULL:
            max_lines = 10000
        
        # HEADER
        parts.append(f"{f.id} | {f.ufid}")
        
        # FULL
        if verbosity >= Verbosity.FULL and f.imports:
            parts.append(textwrap.fill(', '.join(f.imports), width=_LINE_WRAP_WIDTH-len(indent_str), initial_indent=_INDENT_TAB, subsequent_indent=_INDENT_TAB))

        # SIMPLE
        if verbosity >= Verbosity.SIMPLE:
            if f.fields:
                parts.append(f"fields: {', '.join(f.fields.keys())}")
            if f.methods:
                parts.append("\n".join([cls.dump_method(m, Verbosity.SKELETON, indent=indent+1, pretty=pretty) for m in f.methods.values()]))
        
        # SKELETON
        if verbosity >= Verbosity.SKELETON:
            for c in f.classes:
                parts.append(cls.dump_class(c, verbosity=verbosity-1, indent=indent+1, pretty=pretty))
                
        return textwrap.indent("\n".join(parts), indent_str)
    
    @classmethod
    def dump_parser(cls, parser: "BaseParser", verbosity: Verbosity=Verbosity.SIMPLE, pretty: bool = True) -> str:
        return '\n\n'.join([cls.dump_file(f, verbosity, pretty=pretty) for f in parser.files])
    
    @classmethod
    def dump_files(cls, files: list[BaseFile], verbosity: Verbosity=Verbosity.SIMPLE, pretty: bool = True)->str:
        return '\n' + '\n\n'.join([cls.dump_file(f, verbosity, pretty=pretty) for f in files])
