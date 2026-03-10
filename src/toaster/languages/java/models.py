from dataclasses import dataclass
from toaster.core.models import BaseFile, BaseClass, BaseMethod, BaseField

@dataclass
class JavaFile(BaseFile):
    pass

@dataclass
class JavaField(BaseField):
    ACCESS_MODIFIERS = {"public", "protected", "private"}

@dataclass
class JavaClass(BaseClass):
    ACCESS_MODIFIERS = {"public", "protected", "private"}
    
    def skeletonize(self) -> str:
        replacements = []
        class_start_byte = self.node.start_byte
        
        for method in self.methods.values():
            method_node = method.node
            method_description = method.description
            
            if not method_description:
                continue
            
            body_node = None
            for child in method_node.children:
                if child.type == 'block':
                    body_node = child
                    break
            if body_node:
                rel_start = body_node.start_byte - class_start_byte
                rel_end = body_node.end_byte - class_start_byte
                replacements.append({
                    "start": rel_start,
                    "end": rel_end,
                    "text": f"{{\n    // {method_description}\n    }}"
                })
        replacements.sort(key=lambda x: x["start"], reverse=True)
        
        modified_source = self.node.text
        for rep in replacements:
            modified_source = (
                modified_source[:rep["start"]] + 
                rep["text"].encode('utf-8') + 
                modified_source[rep["end"]:]
            )

        return modified_source.decode('utf-8')

@dataclass
class JavaMethod(BaseMethod):
    ACCESS_MODIFIERS = {"public", "protected", "private"}

    def _link_dependencies(self, candidates: list, is_local: bool) -> None:
        self_ref = f"{self.id}|#{self.umid.split('#')[-1]}" if is_local else f"{self.id}|{self.umid}"
        
        def target_ref(c):
            return f"{c.id}|#{c.umid.split('#')[-1]}" if is_local else f"{c.id}|{c.umid}"

        def fallback_ref(c):
            return f"~#{c.identifier}(?)" if is_local else f"~{c.identifier}(?)"

        if len(candidates) == 1:
            c = candidates[0]
            c.inbound_dependencies.append(self_ref)
            self.dependencies.append(target_ref(c))
            return

        for c in candidates:
            c.inbound_dependencies.append(f"~{self_ref}")
            
        if len(candidates) <= 3:
            self.dependencies.extend([f"~{target_ref(c)}" for c in candidates])
        else:
            self.dependencies.append(fallback_ref(candidates[0]))

    def resolve_dependencies(self, imports: list[str]) -> None:
        if not self.dependency_names:
            return
        
        parent_class = self.umid.split('#')[0] if '#' in self.umid else self.umid.rsplit('.', 1)[0]
        
        for text, identifier in set(self.dependency_names):
            param_str = text.split('(')[-1].strip(')')
            arity = 0 if not param_str else len(param_str.split(','))
            
            local_name = f"{parent_class}.{identifier}"
            local_candidates = [c for c in self.registry.map_scoped.get(local_name, []) if c.arity == arity]
            
            if local_candidates:
                self._link_dependencies(local_candidates, is_local=True)
                continue
            
            import_candidates = []
            for imp in imports:
                import_name = f"{imp}.{identifier}"
                import_candidates.extend(self.registry.map_scoped.get(import_name, []))
                
            import_candidates = [c for c in import_candidates if c.arity == arity]
            
            if import_candidates:
                self._link_dependencies(import_candidates, is_local=False)
                continue
            
            global_candidates = [c for c in self.registry.map_short.get(identifier, []) if c.arity == arity]
            
            if global_candidates:
                self._link_dependencies(global_candidates, is_local=False)
                continue
            
            self.unresolved_dependencies.append(identifier)
            
        self.dependencies = list(set(self.dependencies))


@dataclass
class JavaEnum(JavaClass):
    pass