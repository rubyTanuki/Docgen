from Languages.Java import JavaParser
from llm_client import GeminiClient
import asyncio
import time
import os
import json
import toons
from member_registry import MemberRegistry



async def main():
    FILEPATH = "TestCode/gson"
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY is None:
        raise ValueError("API key not found. Set the GEMINI_API_KEY environment variable.")

    llm = GeminiClient(api_key=GEMINI_API_KEY)
    print("Generating AST...")
    start_time = time.perf_counter()
    parser = JavaParser(FILEPATH, llm)
    await parser.parse(use_cache=True)
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Generated AST w/ descriptions in {elapsed_time:.4f} seconds.")
    
    toons_string = toons.dumps(parser.__json__(), indent=4)
    with open(FILEPATH + "/skeleton_test.toon", "w") as file:
        file.write(toons_string)
        
    method_cache = json.dumps(MemberRegistry.get_method_cache(), indent=4)
    with open(FILEPATH + "/.toaster_cache.json", "w") as file:
        file.write(method_cache)

if __name__ == "__main__":
    asyncio.run(main())