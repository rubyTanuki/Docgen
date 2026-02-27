from toaster.core import BaseParser

class JavaParser(BaseParser):
    def __init__(self, project_dir:str, llm=None, registry=None):
        super().__init__(project_dir, llm, registry)
    
    async def parse(self, query="*.java", use_cache=True):
        await super().parse(query, use_cache)