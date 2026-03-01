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
    def dump_method(cls, m: BaseMethod, verbosity: Verbosity=Verbosity.SIMPLE) -> str:
        output = f"\n{m.id} @L{m.line} | {m.signature}"
        
        if verbosity>Verbosity.MINIMAL:
            # append description
            output+= f"\n// {m.description}"
            # append outbound dependencies
            if m.dependencies:
                output += '\n>' + ', '.join(m.dependencies)
            
        if verbosity>Verbosity.SIMPLE:
            # append inbound dependencies
            if m.inbound_dependencies:
                output += '<' + ', '.join(m.inbound_dependencies)
        
        if verbosity==Verbosity.FULL:
            # append full body
            output += f"\n{m.body}"
        
        return output
        
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
    
