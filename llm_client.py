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
        self.semaphore = asyncio.Semaphore(200)
    
    async def generate_description(self, class_obj: "BaseClass", imports: list[str]) -> dict:
        system_instruction = """
You are an expert senior software engineer and technical writer. 
Your goal is to generate high-quality, information-dense documentation for software methods to be consumed by an AI Agent.
The descriptions should be written in context; docs dont need to say 'this is a java class' or this is a method'.
Assume all descriptions are to be utilized by an AI Agent for contextual reference as a human would use JavaDocs to understand a class.

### TASK
Analyze the provided code and generate a JSON response. 
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
        
        if not has_cached_methods:
            # COLD START: Send the raw class body, but provide the ID mapping so the LLM knows what IDs to return
            input_data = {
                "code": class_obj.body,
                "ucid": class_obj.ucid,
                "imports": imports,
                "method_ids_to_signatures": {idx: m.signature for idx, m in method_lookup.items()},
                "child_classes": [c.signature for c in class_obj.child_classes.values()]
            }
        else:
            system_instruction += "\nONLY RETURN DETAILS FOR METHODS NOT IN CACHE. "
            print(f"Cache contains descriptions for {class_obj.ucid}, only generating missing descriptions...")
            # WARM START: Swap raw code for descriptions where possible, keyed by integer ID
            input_data = {
                "ucid": class_obj.ucid,
                "fields": [f.signature for f in class_obj.fields.values()],
                "cached_methods": {
                    idx: m.description 
                    for idx, m in method_lookup.items() 
                    if m.description},
                "methods_to_generate": {
                    idx: m.body 
                    for idx, m in method_lookup.items()
                    if not m.description
                },
                "imports": imports,
                "child_classes": {c.signature: c.description for c in class_obj.child_classes.values()}
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