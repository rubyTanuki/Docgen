from Languages.Agnostic import BaseParser

class JavaParser(BaseParser):
    def __init__(self, project_dir:str):
        super().__init__(project_dir)
    
    def parse(self):
        super().parse("*.java")