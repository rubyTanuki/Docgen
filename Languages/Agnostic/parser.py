from .models import BaseFile

from pathlib import Path
from abc import ABC
from collections import defaultdict
import toons

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
                suffix = filepath.suffix
                name = filepath.name
                
                file_obj = None
                
                # 1. Create the Object
                match(suffix):
                    case ".java":
                        file_obj = JavaFile.from_source(name, code)
                
                # 2. Attach the source path (Critical for distributed context)
                if file_obj:
                    file_obj.source_path = filepath 
                    self.files.append(file_obj)

        # 3. Resolve Dependencies (Global Pass)
        for file in self.files:
            # Assuming your resolve_dependencies handles the logic internally
            # or you might need to pass self.files/imports here depending on your impl
            file.resolve_dependencies()

    def resolve_descriptions(self, llm: "LLMClient"):
        for file in self.files:
            file.resolve_descriptions(llm)

    def generate_distributed_context(self, output_filename="_context.toon"):
        """
        Groups files by their directory and writes a skeleton .toon file
        into each folder.
        """
        # 1. Group files by Directory
        dir_map = defaultdict(list)
        for f in self.files:
            # We use the 'source_path' we attached during parse()
            if hasattr(f, 'source_path'):
                parent_dir = f.source_path.parent
                dir_map[parent_dir].append(f)

        # 2. Write the .toon files
        count = 0
        for folder_path, files in dir_map.items():
            # Create the data payload for JUST this folder
            folder_data = [f.__json__() for f in files]
            
            # Dump to string
            toon_string = toons.dumps(folder_data, indent=4)
            
            # Write to the sub-directory
            target_file = folder_path / output_filename
            with open(target_file, "w") as out:
                out.write(toon_string)
            
            count += 1
            
        print(f"✅ Generated distributed context in {count} directories.")

    def __json__(self):
        return [f.__json__() for f in self.files]
    
    def __skeleton__(self):
        return {f"{f.package}.{f.filename}" if f.package else f.filename: f.__skeleton__() for f in self.files}