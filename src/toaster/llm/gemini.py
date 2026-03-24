import asyncio
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import time

class MethodDescription(BaseModel):
    method_id: int = Field(description="The integer ID of the method provided in the prompt data")
    description: str = Field(description="Description of the method")
    confidence: int = Field(description="Confidence in analysis based only on provided code")
    needs_context: int = Field(description="Dependency on external/unknown state (0=Pure, 100=Dependent on external logic)")

class DescriptionResult(BaseModel):
    ucid: str = Field(description="ucid of the class")
    description: str = Field(description="Description of the class")
    confidence: int = Field(description="Confidence in analysis based only on provided code")
    needs_context: int = Field(description="Dependency on external/unknown state (0=Pure, 100=Dependent on external logic)")
    methods: list[MethodDescription] = Field(description="List of method information")

class GeminiClient:
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash-lite"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        self._semaphore = None
    
    @property
    def semaphore(self):
        # 2. Create it exactly once, the first time it is requested
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(200)
        return self._semaphore
    
    async def generate_description(self, class_obj: "BaseClass", imports: list[str]) -> dict:
        system_instruction = """
You are an expert senior software engineer and technical writer. 
Your goal is to generate high-quality, information-dense documentation for software methods to be consumed by an AI Agent.
The descriptions should be written in context; docs dont need to say 'this is a java class' or this is a method'.
Assume all descriptions are to be utilized by an AI Agent for contextual reference as a human would use JavaDocs to understand a class.

### TASK
Analyze the provided code and generate a JSON response. 
**Class Analysis**: Generate a `description` for the overall class. Look at the fields, Javadocs, and method summaries to write a concise explanation of the class's primary purpose and architectural role. Also provide a confidence score and context need score for the class.
**Method Analysis**: For each method that still has a raw code body, generate:
1. **Description**: Write a concise summary of what the method does. 
   - **Focus on**: Inputs and Outputs (semantics) and Side Effects (state changes). If the method is complex, include core logic (algorithms and data flow).
   - **Style**: Technical, precise, and dense. Start with an active verb (e.g., "Calculates...", "Updates..."). Unless complexity is high, try to keep it to one sentence.
2. **Confidence Score (1-100)**: Confidence in analysis based only on provided code. Should only be 100 for simple getters/setters.
3. **Context Need Score (1-100)**: Dependency on external/unknown state, such as database access, unknown imports, not easily-resolvable dependencies (0=Pure, 100=Dependent on external logic).
Reference methods by their provided integer `method_id`.
"""
        
        # Create a mapping of method IDs to method objects
        method_lookup = {idx: m for idx, m in enumerate(class_obj.methods.values())}
        
        has_cached_methods = any(m.description for m in class_obj.methods.values())
        
        
        input_data = {
            "code": class_obj.skeletonize(),
            "method_ids_to_signatures": {idx: m.signature for idx, m in method_lookup.items()}
        }
        
        print(f"Generating Description for {class_obj.ucid}...")
        start_time = time.perf_counter()
        
        max_retries = 3
        base_delay = 2
        
        async with self.semaphore:
            for attempt in range(max_retries):
                try: 
                    response = await self.client.aio.models.generate_content(
                        model=self.model_name,
                        contents=json.dumps(input_data),
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            response_mime_type="application/json",
                            response_json_schema=DescriptionResult.model_json_schema(),
                            temperature=0.2,
                            max_output_tokens=8192
                        )
                    )
                    end_time = time.perf_counter()
                    elapsed_time = end_time - start_time
                    print(f"✅ Generated Description for {class_obj.ucid} in {elapsed_time:.4f} seconds.")
                    
                    parsed_data = response.parsed
                    
                    # Re-map the returned integers back to their actual string UMIDs
                    for method_result in parsed_data.get("methods", []):
                        m_id = method_result.get("method_id")
                        if m_id in method_lookup:
                            method_result["umid"] = method_lookup[m_id].umid
                            
                    # if not parsed_data["description"]:
                    #     print("no class level description found")
                    return parsed_data
                    
                except Exception as e:
                    error_str = str(e)
                    if "503" in error_str or "429" in error_str:
                        if attempt < max_retries - 1:
                            sleep_time = base_delay * (2 ** attempt)
                            print(f"⏳ Server busy (503/429) on {class_obj.ucid}. Retrying in {sleep_time}s...")
                            await asyncio.sleep(sleep_time)
                            continue 
                            
                    return {
                        "ucid": class_obj.ucid,
                        "error": error_str,
                        "status": "error"
                    }