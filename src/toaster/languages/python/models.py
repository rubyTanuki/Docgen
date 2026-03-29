from dataclasses import dataclass
from toaster.core.models import BaseFile, BaseClass, BaseMethod, BaseField

@dataclass
class PythonFile(BaseFile):
    pass

@dataclass
class PythonField(BaseField):
    pass

@dataclass
class PythonClass(BaseClass):
    def skeletonize(self) -> str:
        if not self.node:
            return self.body

        replacements = []
        class_start_byte = self.node.start_byte

        for method in self.methods.values():
            if not method.node or not method.description:
                continue

            method_body = method.node.child_by_field_name("body")
            if method_body:
                rel_start = method_body.start_byte - class_start_byte
                rel_end = method_body.end_byte - class_start_byte

                replacements.append(
                    {
                        "start": rel_start,
                        "end": rel_end,
                        "text": f"...\n    # {method.description}".encode("utf-8"),
                    }
                )

        replacements.sort(key=lambda x: x["start"], reverse=True)

        modified_source = self.node.text
        for rep in replacements:
            modified_source = (
                modified_source[: rep["start"]]
                + rep["text"]
                + modified_source[rep["end"] :]
            )

        return modified_source.decode("utf-8")

@dataclass
class PythonMethod(BaseMethod):
    def _link_dependencies(self, candidates: list, is_local: bool) -> None:
        self_ref = (
            f"{self.id}|#{self.umid.split('#')[-1]}"
            if is_local
            else f"{self.id}|{self.umid}"
        )

        def target_ref(c):
            return (
                f"{c.id}|#{c.umid.split('#')[-1]}"
                if is_local
                else f"{c.id}|{c.umid}"
            )

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

        parent_class_name = (
            self.umid.split("#")[0]
            if "#" in self.umid
            else self.umid.rsplit(".", 1)[0]
        )

        for identifier, call_arity in set(self.dependency_names):
            # For Python, we relax the arity check: call_arity <= candidate.arity
            # This accounts for default parameters.

            def match_arity(c):
                return call_arity <= c.arity

            local_name = f"{parent_class_name}.{identifier}"
            local_candidates = [
                c
                for c in self.registry.map_scoped.get(local_name, [])
                if match_arity(c)
            ]

            if local_candidates:
                self._link_dependencies(local_candidates, is_local=True)
                continue

            import_candidates = []
            for imp in imports:
                import_name = f"{imp}.{identifier}"
                import_candidates.extend(self.registry.map_scoped.get(import_name, []))

            import_candidates = [c for c in import_candidates if match_arity(c)]

            if import_candidates:
                self._link_dependencies(import_candidates, is_local=False)
                continue

            global_candidates = [
                c
                for c in self.registry.map_short.get(identifier, [])
                if match_arity(c)
            ]

            if global_candidates:
                self._link_dependencies(global_candidates, is_local=False)
                continue

            self.unresolved_dependencies.append(identifier)

        self.dependencies = list(set(self.dependencies))

@dataclass
class PythonEnum(PythonClass):
    pass
