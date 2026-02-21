import os
import hashlib
import re
from typing import List, Dict, Any, Optional
from tree_sitter import Node, Query, QueryCursor, Parser

from Languages.Java.queries import DEPENDENCY_QUERY
from Languages.Java.language import JAVA_LANGUAGE

from member_registry import MemberRegistry
from Languages.Agnostic import BaseFile, BaseClass, BaseMethod, BaseField, BaseEnum

class JavaFile(BaseFile):
    def __init__(self, ufid: str, imports: list[str], classes: list["JavaClass"]):
        # BaseFile init: (ufid, imports, classes)
        super().__init__(ufid, imports, classes)

    @classmethod
    def from_source(cls, filename: str, source_code: bytes) -> "JavaFile":
        parser = Parser()
        parser.language = JAVA_LANGUAGE
        tree = parser.parse(source_code)
        root_node = tree.root_node
        
        scope = ""
        imports = []
        classes = []

        for child in root_node.children:
            if child.type == "package_declaration":
                # package com.example; -> child[1] is the identifier
                for grandchild in child.children:
                    if grandchild.type in {"scoped_identifier", "identifier"}:
                        scope = grandchild.text.decode('utf-8')
                        break
            elif child.type == "import_declaration":
                # import java.util.List;
                for grandchild in child.children:
                    if grandchild.type in {"scoped_identifier", "identifier"}:
                        imports.append(grandchild.text.decode('utf-8'))
            elif child.type == "class_declaration":
                java_class = JavaClass.from_node(child, scope)
                classes.append(java_class)

        return cls(filename, imports, classes)

    @classmethod
    def from_file(cls, filepath: str) -> "JavaFile":
        with open(filepath, "rb") as f:
            source = f.read()
        return cls.from_source(os.path.basename(filepath), source)


class JavaClass(BaseClass):
    
    ACCESS_MODIFIERS = {"public", "protected", "private"}

    def __init__(self, ucid: str, signature: str, body: str):
        # BaseClass init: (ucid, signature, body)
        super().__init__(ucid, signature, body)
        
        # Override types for Java specifics if needed, but Base dicts work fine
        self.fields: Dict[str, "JavaField"] = {}
        self.methods: Dict[str, "JavaMethod"] = {}
        self.child_classes: Dict[str, "JavaClass"] = {}

    @classmethod
    def from_node(cls, node: "Node", scope: str = "") -> "JavaClass":
        identifier: str = ""
        superclass: str = ""
        modifiers: List[str] = []
        interfaces: List[str] = []
        type_params: List[str] = []
        body_node = None
        
        identifier_node = node.child_by_field_name('name')
        if identifier_node:
            identifier = identifier_node.text.decode('utf-8')
        
        ucid = f"{scope}.{identifier}" if scope else identifier

        for child in node.children:
            child_type = child.type
            
            if child_type == "modifiers":
                modifiers = child.text.decode('utf-8').split()
            elif child_type == "type_parameters":
                type_params.append(child.text.decode('utf-8'))
            elif child_type == "superclass":
                for gc in child.children:
                    if "type" in gc.type:
                        superclass = gc.text.decode('utf-8')
            elif child_type == "super_interfaces":
                type_list = child.child_by_field_name('interfaces')
                if type_list:
                    interfaces = [c.text.decode('utf-8') for c in type_list.children if "type" in c.type]
            elif child_type == "class_body":
                body_node = child

        # Construct Signature
        access = "package-private"
        other_mods = []
        
        for mod in modifiers:
            if mod in cls.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)
        
        generics_str = f"{''.join(type_params)}" if type_params else ""
        
        sig_parts = [access] + other_mods + ["class", identifier + generics_str]
        
        if superclass:
            sig_parts.append(f"extends {superclass}")
        if interfaces:
            sig_parts.append(f"implements {', '.join(interfaces)}")
            
        signature = " ".join(filter(None, sig_parts))
        
        final_body = body_node.text.decode('utf-8') if body_node else ""

        instance = cls(ucid, signature, final_body)

        # Parse Body
        if body_node:
            for child in body_node.children:
                ct = child.type
                
                if ct in ("method_declaration", "constructor_declaration"):
                    method = JavaMethod.from_node(child, instance.ucid)
                    instance.methods[method.umid] = method
                    MemberRegistry.add_method(method)
                    
                elif ct == "field_declaration":
                    field = JavaField.from_node(child, instance.ucid)
                    instance.fields[field.ucid] = field
                    
                elif ct == "class_declaration":
                    child_class = JavaClass.from_node(child, scope=instance.ucid)
                    instance.child_classes[child_class.ucid] = child_class

        return instance


class JavaField(BaseField):
    
    ACCESS_MODIFIERS = {"public", "protected", "private"}

    def __init__(self, ucid: str, name: str, signature: str, field_type: str):
        # BaseField init: (ucid, name, signature)
        super().__init__(ucid, name, signature, field_type)

    @classmethod
    def from_node(cls, node: "Node", scope: str = "") -> "JavaField":
        type_text: str = ""
        modifiers: List[str] = []
        identifier: str = "Unknown"
        value: str = ""
        
        type_node = node.child_by_field_name('type')
        if type_node:
            type_text = type_node.text.decode('utf-8')

        for child in node.children:
            child_type = child.type
            if child_type == "modifiers":
                modifiers = child.text.decode('utf-8').split()
            elif child_type == "variable_declarator":
                name_node = child.child_by_field_name('name')
                if name_node:
                    identifier = name_node.text.decode('utf-8')
                value_node = child.child_by_field_name('value')
                if value_node:
                    value = value_node.text.decode('utf-8')
                break

        # ucid: "com.example.MyClass.myField"
        ucid = f"{scope}.{identifier}" if scope else identifier

        access = "package-private"
        other_mods = []
        for mod in modifiers:
            if mod in cls.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)

        sig_parts = [access] + other_mods + [type_text, identifier]
        signature = " ".join(filter(None, sig_parts))
        
        if value:
            signature += f" = {value}"

        return cls(ucid, identifier, signature, type_text)


class JavaMethod(BaseMethod):
    
    _DEP_QUERY = Query(JAVA_LANGUAGE, DEPENDENCY_QUERY)
    ACCESS_MODIFIERS = {"public", "protected", "private"}
    
    def __init__(self, identifier: str, scoped_identifier: str, return_type: str, umid: str, signature: str, body: str, body_hash: str, 
                 dependency_names: List[str], line: int, parameters: List[str]):
        # BaseMethod init: (umid, signature, body, body_hash, dependency_names)
        super().__init__(identifier, scoped_identifier, return_type, umid, signature, body, body_hash, dependency_names, line, parameters)
    
    @classmethod
    def from_node(cls, node: "Node", scope: str, dep_query: "Query" = None) -> "JavaMethod":
        line = node.start_point[0]
        
        identifier = "<init>"
        return_type = "void"
        
        name_node = node.child_by_field_name('name')
        if name_node:
            identifier = name_node.text.decode('utf-8')
            
        if node.type != 'constructor_declaration':
            type_node = node.child_by_field_name('type')
            if type_node:
                return_type = type_node.text.decode('utf-8')
            elif node.child_by_field_name('dimensions'):
                return_type = "void"
                
        params_full = []
        params_types = []
        
        params_node = node.child_by_field_name('parameters')
        if params_node:
            for child in params_node.children:
                if child.type in ("formal_parameter", "spread_parameter"):
                    params_full.append(child.text.decode('utf-8'))
                    
                    t_node = child.child_by_field_name('type')
                    if t_node:
                        params_types.append(t_node.text.decode('utf-8'))
                    else:
                        params_types.append(child.text.decode('utf-8').split()[0])
        
        # UMID Construction
        umid = f"{scope}#{identifier}({','.join(params_types)})"
        scoped_identifier = f"{scope}.{identifier}"
        
        modifiers = []
        throws_clause = ""
        type_params = ""
        
        for child in node.children:
            ct = child.type
            if ct == "modifiers":
                modifiers = child.text.decode('utf-8').split()
            elif ct == "type_parameters":
                type_params = child.text.decode('utf-8')
            elif ct == "throws":
                throws_clause = child.text.decode('utf-8')
                
        access = "package-private"
        other_mods = []
        for mod in modifiers:
            if mod in cls.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)
                
        sig_parts = [access] + other_mods + [type_params, return_type, identifier]
        if return_type == "void" and node.type == 'constructor_declaration':
            sig_parts.remove("void")
            return_type = "<constructor>"
             
        full_sig_str = f"{' '.join(filter(None, sig_parts))}({', '.join(params_full)})"
        if throws_clause:
            full_sig_str += f" {throws_clause}"
        
        body = ""
        body_hash = ""
        dependency_names = []

        body_node = node.child_by_field_name('body')
        if body_node:
            body = body_node.text.decode('utf-8')
            clean_body = re.sub(r'\s+', '', body)
            body_hash = hashlib.sha256(clean_body.encode('utf-8')).hexdigest()[:8]
            
            # Use class level query if none provided
            cursor = QueryCursor(JavaMethod._DEP_QUERY)
            
            captures = cursor.captures(body_node)
            # Tree-sitter python bindings vary by version. 
            # This handles the common case: dict of {name: [nodes]}
            if isinstance(captures, dict) and "dependencies" in captures:
                for d_node in captures["dependencies"]:
                    dependency_names.append(d_node.text.decode('utf-8'))
            # Handle list of tuples case [(node, name)]
            elif isinstance(captures, list):
                for d_node, name in captures:
                    if name == "dependencies":
                        dependency_names.append(d_node.text.decode('utf-8'))
                            
        return cls(identifier, scoped_identifier, return_type, umid, full_sig_str, body, body_hash, dependency_names, line, parameters=params_full)
    
    def resolve_dependencies(self, imports: List[str]) -> None:
        if not self.dependency_names:
            return
        
        unique_names = set(self.dependency_names)
        
        if '#' in self.umid:
            parent_class = self.umid.split('#')[0]
        else:
            parent_class = self.umid.rsplit('.', 1)[0]
        
        
        
        for name in unique_names:
            parameters = name.split('(')[-1].strip(')').split(',')
            arity = len(parameters)
            # 1. Local Check
            local_fullname = f"{parent_class}.{name}"
            if local_fullname in MemberRegistry.map_scoped:
                candidates = MemberRegistry.map_scoped[local_fullname]
                if len(candidates) == 1:
                    self.dependencies.append(f"#{candidates[0].umid.split('#')[-1]}")
                else:
                    self.dependencies.extend([f"(candidate)#{c.umid.split('#')[-1]}" for c in candidates if c.arity == arity])
                continue
            
            # 2. Import Check
            resolved_via_import = False
            candidates = []
            for imp in imports:
                import_fullname = f"{imp}.{name}"
                if import_fullname in MemberRegistry.map_scoped:
                    candidates.extend(MemberRegistry.map_scoped[import_fullname])
            if candidates:
                if len(candidates) == 1:
                    self.dependencies.append(candidates[0].umid)
                else:
                    self.dependencies.extend([f"{c.umid}" for c in candidates if c.arity == arity])
                continue
            
            # 3. Global Name Check
            if name in MemberRegistry.map_short:
                candidates = MemberRegistry.map_short[name]
                if len(candidates) == 1:
                    self.dependencies.append(candidates[0].umid)
                else:
                    self.dependencies.extend([f"(candidate){c.umid}" for c in candidates if c.arity == arity])
                continue
            
            self.unresolved_dependencies.append(name)
        # remove duplicates
        self.dependencies = list(set(self.dependencies))
        if self in self.dependencies:
            self.dependencies.remove(self)


class JavaEnum(BaseEnum):
    
    ACCESS_MODIFIERS = {"public", "protected", "private"}

    def __init__(self, ucid: str, signature: str, body: str, constants: List[str]):
        # BaseEnum init: (ucid, signature, body, constants)
        super().__init__(ucid, signature, body, constants)

        # BaseClass (parent of BaseEnum) already defines fields/methods dicts
        # We don't need to redefine them unless we want strict typing hints
        self.fields: Dict[str, "JavaField"] = {}
        self.methods: Dict[str, "JavaMethod"] = {}

    @classmethod
    def from_node(cls, node: "Node", scope: str = "") -> "JavaEnum":
        identifier: str = ""
        modifiers: List[str] = []
        interfaces: List[str] = []
        constants: List[str] = []
        body_node = None
        
        name_node = node.child_by_field_name('name')
        if name_node:
            identifier = name_node.text.decode('utf-8')

        ucid = f"{scope}.{identifier}" if scope else identifier

        for child in node.children:
            child_type = child.type
            if child_type == "modifiers":
                modifiers = child.text.decode('utf-8').split()
            elif child_type == "super_interfaces":
                type_list = child.child_by_field_name('interfaces')
                if type_list:
                    interfaces = [c.text.decode('utf-8') for c in type_list.children if "type" in c.type]
                else:
                    interfaces = [c.text.decode('utf-8') for c in child.children if "type" in c.type]
            elif child_type == "enum_body":
                body_node = child

        # Signature 
        access = "package-private"
        other_mods = []
        for mod in modifiers:
            if mod in cls.ACCESS_MODIFIERS:
                access = mod
            else:
                other_mods.append(mod)

        sig_parts = [access] + other_mods + ["enum", identifier]
        if interfaces:
            sig_parts.append(f"implements {', '.join(interfaces)}")
        final_signature = " ".join(filter(None, sig_parts))
        
        final_body = body_node.text.decode('utf-8') if body_node else ""
        
        instance = cls(ucid, final_signature, final_body, constants)

        # Attach members
        if body_node:
            for child in body_node.children:
                ct = child.type
                
                if ct == "enum_constant":
                    const_name = child.child_by_field_name('name').text.decode('utf-8')
                    args_node = child.child_by_field_name('arguments')
                    if args_node:
                        const_name += args_node.text.decode('utf-8')
                    instance.constants.append(const_name)

                elif ct in ("method_declaration", "constructor_declaration"):
                    method = JavaMethod.from_node(child, instance.ucid)
                    # Use UMID key (Flat Dict)
                    instance.methods[method.umid] = method
                    
                elif ct == "field_declaration":
                    field = JavaField.from_node(child, instance.ucid)
                    instance.fields[field.ucid] = field

        return instance

    def resolve_dependencies(self):
        """Recursively resolve dependencies for all methods."""
        for method in self.methods.values():
            method.resolve_dependencies([])