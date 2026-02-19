from Languages.Agnostic import BaseParser

class JavaParser(BaseParser):
    def __init__(self, project_dir:str, llm=None):
        super().__init__(project_dir, llm)
    
    async def parse(self, query="*.java"):
        await super().parse(query)