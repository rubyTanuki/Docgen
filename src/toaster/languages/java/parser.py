from toaster.core import BaseParser
from toaster.languages.java.builder import JavaBuilder

class JavaParser(BaseParser):     
    def parse_file(self, name: str, code: bytes):
        if not name.endswith(".java"):
            return None
        builder = JavaBuilder(self.registry)
        return builder.parse_source(name, code)