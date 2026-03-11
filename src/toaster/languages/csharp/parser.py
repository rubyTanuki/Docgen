from toaster.core import BaseParser
from toaster.languages.csharp.builder import CSharpBuilder

class CSharpParser(BaseParser):     
    def parse_file(self, name: str, code: bytes):
        if not name.endswith(".cs"):
            return None
        builder = CSharpBuilder(self.registry)
        return builder.parse_source(name, code)
