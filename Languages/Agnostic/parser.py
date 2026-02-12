from .models import BaseFile

from pathlib import Path
from abc import ABC


class BaseParser(ABC):
    def __init__(self, project_dir: str):
        self.files: list[BaseFile] = []
        self.project_dir = project_dir

    def parse(self, query="*"):
        from Languages.Java import JavaFile

        path = Path(self.project_dir)

        for filepath in path.rglob(query):
            if filepath.is_file():
                code = filepath.read_bytes()
                type = filepath.suffix
                name = filepath.name
                match(type):
                    case ".java":
                        self.files.append(JavaFile.from_source(name, code))

        for file in self.files:
            file.resolve_dependencies()