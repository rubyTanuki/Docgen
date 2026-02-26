import argparse
import asyncio
import os
import sys
import time
import json
from pathlib import Path

from toaster.llm import GeminiClient
from toaster.core import MemberRegistry, toast
from toaster.languages.java import JavaParser


def main():
    asyncio.run(run_cli())

async def run_cli():
    cli = argparse.ArgumentParser(
        prog="toaster",
        description="AST scraper for LLM RAG context generation."
    )
    
    cli.add_argument("path", type=str, nargs="?", default=".", help="Path to the project directory to scan (defaults to current directory)")

    args = cli.parse_args()
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY is None:
        print("❌ Error: API key not found. Set the GEMINI_API_KEY environment variable.")
        sys.exit(1)

    # Validate the path
    target_path = Path(args.path)
    if not target_path.exists() or not target_path.is_dir():
        print(f"❌ Error: Directory '{target_path.absolute()}' does not exist.")
        sys.exit(1)

    start_time = time.perf_counter()
    
    # llmClient first for Dependency Injection
    llm = GeminiClient(api_key=GEMINI_API_KEY) 
    
    
    print("🔍 Parsing files and linking AST...")
    parser = JavaParser(target_path, llm)
    await parser.parse(use_cache=True)
    
    # Write Skeleton
    toast_string = toast.dump_project(parser)
    with open(target_path / "skeleton.toast", "w") as file:
        file.write(toast_string)

    # Write Cache
    method_cache = json.dumps(MemberRegistry.get_cache(), indent=4)
    with open(target_path / ".toaster_cache.json", "w") as file:
        file.write(method_cache)
        
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    print(f"✅ Success! Skeleton and cache saved in {elapsed_time:.4f} seconds.")
    
    # # Optional flags
    
    # cli.add_argument("-l", "--lang", type=str, default="java", choices=["java"], 
    #                  help="Target language to parse (default: java)")
    # cli.add_argument("--no-dist", "--root", action="store_true", 
    #                  help="Disable generating distributed context files in subdirectories")
    # cli.add_argument("--clean", action="store_true", 
    #                  help="Remove all generated .toon context and skeleton files in the directory and exit")

    # args = cli.parse_args()
    
    # # 2. Validate the path
    # target_path = Path(args.path)
    # if not target_path.exists() or not target_path.is_dir():
    #     print(f"❌ Error: Directory '{target_path.absolute()}' does not exist.")
    #     sys.exit(1)

    # # 3. Handle the Clean Command
    # if args.clean:
    #     print(f"🧹 Cleaning generated .toon files in {target_path.absolute()}...")
    #     clean_count = 0
        
    #     # Recursively find and delete the specific generated files
    #     for pattern in ["_context.toon", "_skeleton.toon", "skeleton.toon"]:
    #         for file_path in target_path.rglob(pattern):
    #             if file_path.is_file():
    #                 file_path.unlink()  # Deletes the file
    #                 clean_count += 1
    #                 print(f"  Deleted: {file_path.relative_to(target_path)}")
                    
    #     print(f"✨ Clean complete! Removed {clean_count} files.")
    #     sys.exit(0) # Exit after cleaning so we don't accidentally re-parse

    # print(f"🚀 Scanning {args.lang.upper()} project at: {target_path.absolute()}")

    # # --- START TIMER ---
    # start_time = time.perf_counter()

    # # 4. Route to the correct parser
    # if args.lang.lower() == "java":
    #     parser = JavaParser(str(target_path))
    # else:
    #     print(f"🚧 Language '{args.lang}' parsing is not yet implemented.")
    #     sys.exit(1)

    # # 5. Parse files and resolve dependencies
    # print("🔍 Parsing files and linking AST...")
    # parser.parse()
    
    # # 6. Generate distributed sub-contexts (unless disabled)
    # if not args.no_dist:
    #     print("📁 Generating distributed sub-contexts...")
    #     parser.generate_distributed_context()
    
    # # 7. Write Master _context.toon
    # print(f"📝 Writing master _context.toon...")
    # toons_string = toons.dumps(parser.__json__(), indent=4)
    # with open(target_path / "_context.toon", "w") as file:
    #     file.write(toons_string)
        
    # # 8. Write Master _skeleton.toon
    # print(f"🦴 Writing master _skeleton.toon...")
    # skeleton_string = toons.dumps(parser.__skeleton__(), indent=4)
    # with open(target_path / "_skeleton.toon", "w") as file:
    #     file.write(skeleton_string)

    # # --- END TIMER ---
    # end_time = time.perf_counter()
    # elapsed_time = end_time - start_time

    # print(f"✅ Success! Master files saved in {elapsed_time:.4f} seconds.")

if __name__ == "__main__":
    main()