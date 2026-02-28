from toaster.core import BaseParser
from toaster.languages.java.models import JavaFile

class JavaParser(BaseParser):     
    def parse_file(self, name: str, code: bytes):
        if not name.endswith(".java"):
            return None
        return JavaFile.from_source(name, code, self.registry)