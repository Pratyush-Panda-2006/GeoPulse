import os
import time
import json
import base64
import requests
from typing import Optional, Literal, List
from pydantic import BaseModel, Field, ValidationError

NVIDIA_API_KEY_ENV = "NVIDIA_API_KEY"
NEMOTRON_ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
NEMOTRON_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"

# Phase N2: Strict Change-Type Response Contract
class NemotronChangeResponse(BaseModel):
    category: Literal[
        "building_structure",
        "road_highway_infrastructure",
        "mining_excavation",
        "forest_vegetation_disturbance",
        "flood_water_expansion",
        "agricultural_seasonal_change",
        "natural_terrain_geological_change",
        "fire_burn_disturbance",
        "other_known_change",
        "unknown_uncertain"
    ]
    visual_confidence: float = Field(..., ge=0.0, le=1.0)
    short_summary: str
    visual_cues: List[str]
    uncertainty: str
    
    model_config = {
        "extra": "forbid"
    }

NEMOTRON_SYSTEM_PROMPT = """You are an expert SAR (Synthetic Aperture Radar) image interpreter. 

Model 3 has ALREADY DETECTED a significant change in the provided imagery. Do NOT attempt to rediscover whether a change exists. Your sole task is to interpret the TYPE of the detected change based on the visual evidence in the provided T1 (before) and T2 (after) imagery.

You must choose the most plausible CHANGE TYPE from the following exact categories:
1. building_structure
2. road_highway_infrastructure
3. mining_excavation
4. forest_vegetation_disturbance
5. flood_water_expansion
6. agricultural_seasonal_change
7. natural_terrain_geological_change
8. fire_burn_disturbance
9. other_known_change
10. unknown_uncertain

CRITICAL RULES:
- Use "unknown_uncertain" ONLY when the available visual evidence genuinely cannot distinguish a plausible change type (e.g., the region is too small, ambiguous, obscured, or noisy).
- Do NOT make "unknown_uncertain" the default merely because your certainty is below 100%. Prefer the most plausible category supported by visible evidence.
- Never invent details that cannot be visually supported.
- Do not claim exact objects, causes, ownership, legality, intent, or human activity beyond what the imagery supports. Use cautious wording like "possible", "potential", "visually consistent with", "appears consistent with", or "uncertain".
- Avoid unsafe phrases like "confirmed illegal mining", "confirmed construction", "enemy activity", "criminal activity", "this definitely happened because...", or "cause proven".
- This is visual interpretation, not causal proof.

You must respond with ONLY a valid JSON object matching this schema:
{
  "category": "<one of the 10 exact categories above>",
  "visual_confidence": <float between 0.0 and 1.0>,
  "short_summary": "<short human-readable description using cautious wording>",
  "visual_cues": ["<cue 1>", "<cue 2>"],
  "uncertainty": "<string describing limitations of the interpretation>"
}
Do not include markdown blocks or any other text outside the JSON object.
"""

def parse_nemotron_response(content: str) -> NemotronChangeResponse:
    try:
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        data = json.loads(content)
        return NemotronChangeResponse(**data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON: {e}")
    except ValidationError as e:
        raise ValueError(f"Schema validation failed: {e}")

class VisionClassifierClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv(NVIDIA_API_KEY_ENV)
        self.endpoint = NEMOTRON_ENDPOINT
        self.model = NEMOTRON_MODEL
        self.max_retries = 3
        self.timeout_sec = 30
        
    def classify_image(self, system_prompt: str, user_prompt: str) -> str:
        """
        Sends a classification request to the NVIDIA Nemotron model.
        Configured according to N1 foundation requirements.
        """
        if not self.api_key:
            raise ValueError(f"Missing {NVIDIA_API_KEY_ENV} environment variable")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 300
            # tools are explicitly omitted for this phase
        }
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.endpoint, 
                    headers=headers, 
                    json=payload, 
                    timeout=self.timeout_sec
                )
                response.raise_for_status()
                data = response.json()
                
                # Parse the response from message.content
                choices = data.get("choices", [])
                if not choices:
                    raise ValueError("No choices returned in response")
                    
                message = choices[0].get("message", {})
                content = message.get("content", "")
                
                return content
                
            except requests.exceptions.Timeout as e:
                if attempt == self.max_retries - 1:
                    raise TimeoutError(f"NVIDIA API timed out after {self.max_retries} retries") from e
                time.sleep(2 ** attempt)
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    raise RuntimeError(f"NVIDIA API request failed: {e}") from e
                time.sleep(2 ** attempt)

    def classify_image_bytes(self, image_bytes: bytes, user_prompt: str, max_retries_override: Optional[int] = None) -> str:
        """
        Multimodal classification using base64 encoded JPEG bytes.
        """
        if not self.api_key:
            raise ValueError(f"Missing {NVIDIA_API_KEY_ENV} environment variable")

        b64_str = base64.b64encode(image_bytes).decode('utf-8')
        data_uri = f"data:image/jpeg;base64,{b64_str}"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": NEMOTRON_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}}
                    ]
                }
            ],
            "temperature": 0.0,
            "max_tokens": 300
        }

        retries = max_retries_override if max_retries_override is not None else self.max_retries

        for attempt in range(retries):
            try:
                response = requests.post(
                    self.endpoint, 
                    headers=headers, 
                    json=payload, 
                    timeout=self.timeout_sec
                )
                response.raise_for_status()
                data = response.json()
                
                choices = data.get("choices", [])
                if not choices:
                    raise ValueError("No choices returned in response")
                    
                message = choices[0].get("message", {})
                content = message.get("content", "")
                
                return content
                
            except requests.exceptions.Timeout as e:
                if attempt == retries - 1:
                    raise TimeoutError(f"NVIDIA API timed out after {retries} retries") from e
                time.sleep(2 ** attempt)
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise RuntimeError(f"NVIDIA API request failed: {e}") from e
                time.sleep(2 ** attempt)

    def classify_change_type(self, user_prompt: str) -> NemotronChangeResponse:
        """
        End-to-end wrapper for Phase N2 contract.
        """
        content = self.classify_image(NEMOTRON_SYSTEM_PROMPT, user_prompt)
        return parse_nemotron_response(content)
