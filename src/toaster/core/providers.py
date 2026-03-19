from pathlib import Path

from toaster.core.parser import BaseParser
from toaster.languages.java import JavaParser
from toaster.languages.csharp import CSharpParser
from toaster.exceptions import LanguageNotSupportedError

class ParserProvider:
    parser_map = {
        ".java": JavaParser,
        ".cs": CSharpParser
    }
    
    @classmethod
    def get_parser(cls, path: Path, llm: "LLMClient", registry: "MemberRegistry") -> BaseParser:
        files = path.rglob("*")
        for file in files:
            if file.suffix in cls.parser_map.keys():
                return cls.parser_map[file.suffix](path, llm, registry)
        raise LanguageNotSupportedError(f"Unsupported language: {file.suffix}")
        
        