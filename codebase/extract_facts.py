import json
import re
from typing import Dict, List, Any
import requests

class EntityExtractor:
    def __init__(self, api_url: str = "http://localhost:11434/api/generate"):
        self.api_url = api_url
    
    def extract(self, chat_batch: str) -> Dict[str, Any]:
        """Complete extraction with cleanup"""
        raw_response = self._call_model(chat_batch)
        return self._clean_response(raw_response)
    
    def _call_model(self, chat_batch: str) -> str:
        prompt = f"""<|im_start|>system
    You are an entity extraction system. Extract all entities from the chat history and return ONLY valid JSON array.
    Use this exact schema: [{{"type": "PERSON|ORGANIZATION|DATE|LOCATION|PRODUCT", "value": "string"}}]
    Do not include any other text, explanation, or markdown.<|im_end|>
    <|im_start|>user
    Extract entities from this chat history:
    {chat_batch}<|im_end|>
    <|im_start|>assistant
    """
        payload = {
            "model": "sam860/LFM2:350m-Q8_0",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": 512,
                "top_k": 1,
                "stop": ["<|im_start|>", "<|im_end|>"]
            }
        }

        response = requests.post(self.api_url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["response"]
    
    def _clean_response(self, raw_response: str) -> Dict[str, Any]:
        """Clean malformed JSON response"""
        # Remove any markdown code blocks if present
        raw_response = re.sub(r'```json\s*|\s*```', '', raw_response)
        
        try:
            data = json.loads(raw_response)
            if isinstance(data, list):
                # Filter out User role entity and fix "enanti" keys
                cleaned = []
                for item in data:
                    if item.get("value") == "User" or item.get("enanti") == "User":
                        continue
                    if "enanti" in item:
                        item["type"] = item.pop("enanti")
                    cleaned.append(item)
                return {"entities": cleaned}
            return data
        except json.JSONDecodeError:
            return self._regex_extract(raw_response)
    
    def _regex_extract(self, text: str) -> Dict[str, Any]:
        """Emergency fallback"""
        entities = []
        patterns = {
            "PERSON": r'"PERSON",\s*"value":\s*"([A-Z][a-z]+ [A-Z][a-z]+)"',
            "DATE": r'"DATE",\s*"value":\s*"(\d{4}-\d{2}-\d{2})"',
            "PRODUCT": r'"PRODUCT",\s*"value":\s*"([^"]+)"'
        }
        for etype, pattern in patterns.items():
            matches = re.findall(pattern, text)
            for match in matches:
                entities.append({"type": etype, "value": match})
        return {"entities": entities}

chat_batch = """
User: Hi, I need help with my account #12345
Agent: Sure, what's your name?
User: I'm Sarah Johnson
Agent: Thanks Sarah, when did you create the account?
User: On January 15th, 2024
"""

extractor = EntityExtractor()
result = extractor.extract(chat_batch)
print(json.dumps(result, indent=2))