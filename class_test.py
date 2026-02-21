from Languages.Java import JavaFile
from llm_client import GeminiClient
import asyncio
import time
import os
import json
import toons
from toast import toast

java = b"""
package MRILib.util;

public final class Mathf {

    public static final double TAU = Math.PI * 2;
    
    public static double angleWrap(double radian){
        double angle = radian % TAU;
        angle = (angle + TAU) % TAU;
        if(angle > Math.PI)
            angle -= TAU;
        return angle;
    }
}
"""


if __name__ == "__main__":
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    if GEMINI_API_KEY is None:
        raise ValueError("API key not found. Set the GEMINI_API_KEY environment variable.")

    llm = GeminiClient(api_key=GEMINI_API_KEY)
    print("Generating AST...")
    start_time = time.perf_counter()
    file = JavaFile.from_source("MRILib.util.mathf.java", java)
    file.resolve_dependencies()
    class_obj = file.classes[0]
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Generated AST in {elapsed_time:.4f} seconds.")
    
    async def main(file):
        print("Generating First-Pass Descriptions...")
        start_time = time.perf_counter()
        await class_obj.resolve_descriptions(llm, file.imports)
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        # print(json.dumps(file.__json__(), indent=4))
        print(f"Generated Descriptions in {elapsed_time:.4f} seconds.")
        
        toast_string = toast.dump_file(file)
        with open("TestCode/MRILib/skeleton.toast", "w") as file:
            file.write(toast_string)
        
    asyncio.run(main(file))

    
    
    