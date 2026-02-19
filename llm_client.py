import asyncio
import json
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class MethodDescription(BaseModel):
    umid: str = Field(description="umid of the method")
    description: str = Field(description="Description of the method")
    confidence: int = Field(description="Confidence in analysis based only on provided code")
    needs_context: int = Field(description="Dependency on external/unknown state (0=Pure, 100=Dependent on external logic)")
    needs_description: bool = Field(description="True if the method is complex enough to warrant a description (ignore simple getters/setters)")

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
        
        self.semaphore = asyncio.Semaphore(100)

    async def generate_description(self, class_obj: "BaseClass", imports: list[str]) -> dict:
        # Define the system prompt (static instructions)
        system_instruction = """
You are an expert senior software engineer and technical writer. 
Your goal is to generate high-quality, information-dense documentation for software methods to be consumed by an AI Agent.

### TASK
Analyze the provided code and generate a JSON response. 
1. **Description**: Write a concise summary of what the method does. 
   - **Focus on**: Inputs and Outputs (semantics) and Side Effects (state changes). If the method is complex, include core logic (algorithms and data flow).
   - **Style**: Technical, precise, and dense. Start with an active verb (e.g., "Calculates...", "Updates...") Unless complexity is high, try to keep it to one sentence.
2. **Confidence Score (1-100)**: Confidence in analysis based only on provided code. Should only be 100 for simple getters/setters.
3. **Context Need Score (1-100)**: Dependency on external/unknown state, such as database access, unknown imports, not easily-resolvable dependencies (0=Pure, 100=Dependent on external logic).
4. **Needs Description**: True if the method is complex enough to need a description or has context which would be unknown with just the signature(ignore simple getters/setters).
"""


        input_data = {
            "code": class_obj.body,
            "ucid": class_obj.ucid,
            "imports": imports,
            "method_umids": [method.umid for method in class_obj.methods.values()]
        }

        try: 
            async with self.semaphore:
                # 3. Use client.aio for async execution and bundle config
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
            
            # The JSON string is safely retrieved via .text
            return response.parsed
            
        except Exception as e:
            return {
                "ucid": class_obj.ucid,
                "error": str(e),
                "status": "error"
            }