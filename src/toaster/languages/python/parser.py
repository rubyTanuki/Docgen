from toaster.core import BaseParser
from toaster.languages.python.builder import PythonBuilder

class PythonParser(BaseParser):
    def parse_file(self, name: str, code: bytes):
        if not name.endswith(".py"):
            return None

        # Note: name is just the filename here. 
        # The higher level parse_path handles full path filtering.
        builder = PythonBuilder(self.registry)
        return builder.parse_source(name, code)