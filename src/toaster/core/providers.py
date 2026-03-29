from pathlib import Path
from importlib import import_module

from toaster.exceptions import LanguageNotSupportedError


class ParserProvider:
    parser_map = {
        ".java": "toaster.languages.java.JavaParser",
        ".cs": "toaster.languages.csharp.CSharpParser",
        ".py": "toaster.languages.python.PythonParser"
    }
    
    @classmethod
    def get_parser(cls, path: Path, llm: "GeminiClient", registry: "MemberRegistry") -> "BaseParser":
        if path.is_file() and path.suffix in cls.parser_map:
            found_ext = path.suffix
        else:
            # Look for supported files, but ignore common noise directories
            ignore_list = {"venv", ".venv", "env", ".env", "build", "dist", "__pycache__", ".toaster"}
            found_ext = None
            for file in path.rglob("*"):
                if file.suffix in cls.parser_map:
                    if not any(part in file.parts for part in ignore_list):
                        found_ext = file.suffix
                        break
        
        if not found_ext:
            raise LanguageNotSupportedError(f"No supported language files found in {path}")

        full_path = cls.parser_map[found_ext]
        module_path, class_name = full_path.rsplit(".", 1)
        
        module = import_module(module_path)
        parser_class = getattr(module, class_name)
        
        return parser_class(str(path), llm, registry)


class StructProvider:
    struct_map = {
        ".java": {
            "module": "toaster.languages.java.models",
            "file": "JavaFile",
            "class": "JavaClass",
            "method": "JavaMethod",
            "field": "JavaField",
        },
        ".cs": {
            "module": "toaster.languages.csharp.models",
            "file": "CSharpFile",
            "class": "CSharpClass",
            "method": "CSharpMethod",
            "field": "CSharpField",
        },
        ".py": {
            "module": "toaster.languages.python.models",
            "file": "PythonFile",
            "class": "PythonClass",
            "method": "PythonMethod",
            "field": "PythonField",
        },
    }
    
    @classmethod
    def get_struct_class(cls, path: str | Path, struct_type: str) -> "BaseStruct":
        # Path().suffix safely handles filenames without extensions 
        ext = Path(path).suffix.lower()
        
        if ext not in cls.struct_map:
            raise LanguageNotSupportedError(f"Unsupported file extension: {ext}")
            
        config = cls.struct_map[ext]
        
        if struct_type not in config:
            raise ValueError(f"Unknown struct type '{struct_type}' for {ext}")
            
        module = import_module(config["module"])
        return getattr(module, config[struct_type])