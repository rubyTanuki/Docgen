import argparse
import os
import sys
import time  # <-- Added time module
from pathlib import Path

import toons
from Languages.Java import JavaParser

def main():
    # 1. Setup the CLI Arguments
    cli = argparse.ArgumentParser(
        prog="docgen",
        description="AST scraper for LLM RAG context and documentation generation."
    )

    # Positional argument (now optional, defaults to current directory)
    cli.add_argument("path", type=str, nargs="?", default=".", 
                     help="Path to the project directory to scan (defaults to current directory)")
    
    # Optional flags
    cli.add_argument("-l", "--lang", type=str, default="java", choices=["java", "csharp", "python", "js"], 
                     help="Target language to parse (default: java)")
    cli.add_argument("--no-dist", action="store_true", 
                     help="Disable generating distributed context files in subdirectories")
    cli.add_argument("--clean", action="store_true", 
                     help="Remove all generated .toon context and skeleton files in the directory and exit")

    args = cli.parse_args()
    
    # 2. Validate the path
    target_path = Path(args.path)
    if not target_path.exists() or not target_path.is_dir():
        print(f"❌ Error: Directory '{target_path.absolute()}' does not exist.")
        sys.exit(1)

    # 3. Handle the Clean Command
    if args.clean:
        print(f"🧹 Cleaning generated .toon files in {target_path.absolute()}...")
        clean_count = 0
        
        # Recursively find and delete the specific generated files
        for pattern in ["_context.toon", "_skeleton.toon", "skeleton.toon"]:
            for file_path in target_path.rglob(pattern):
                if file_path.is_file():
                    file_path.unlink()  # Deletes the file
                    clean_count += 1
                    print(f"  Deleted: {file_path.relative_to(target_path)}")
                    
        print(f"✨ Clean complete! Removed {clean_count} files.")
        sys.exit(0) # Exit after cleaning so we don't accidentally re-parse

    print(f"🚀 Scanning {args.lang.upper()} project at: {target_path.absolute()}")

    # --- START TIMER ---
    start_time = time.perf_counter()

    # 4. Route to the correct parser
    if args.lang.lower() == "java":
        parser = JavaParser(str(target_path))
    else:
        print(f"🚧 Language '{args.lang}' parsing is not yet implemented.")
        sys.exit(1)

    # 5. Parse files and resolve dependencies
    print("🔍 Parsing files and linking AST...")
    parser.parse()
    
    # 6. Generate distributed sub-contexts (unless disabled)
    if not args.no_dist:
        print("📁 Generating distributed sub-contexts...")
        parser.generate_distributed_context()
    
    # 7. Write Master _context.toon
    print(f"📝 Writing master _context.toon...")
    toons_string = toons.dumps(parser.__json__(), indent=4)
    with open(target_path / "_context.toon", "w") as file:
        file.write(toons_string)
        
    # 8. Write Master _skeleton.toon
    print(f"🦴 Writing master _skeleton.toon...")
    skeleton_string = toons.dumps(parser.__skeleton__(), indent=4)
    with open(target_path / "_skeleton.toon", "w") as file:
        file.write(skeleton_string)

    # --- END TIMER ---
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    print(f"✅ Success! Master files saved in {elapsed_time:.3f} seconds.")

if __name__ == "__main__":
    main()