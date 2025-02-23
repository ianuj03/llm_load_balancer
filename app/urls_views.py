import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .key_pool import select_best_key
from .utils import estimate_tokens
from aisuite.client import Client

router = APIRouter()

class LLMRequest(BaseModel):
    prompt: str
    model: str  # model to use, e.g. "openai:gpt-4o", per aisuite's convention
    region: str = None  # Optional; defaults to a region (e.g., "us-east")

@router.post("/api/llm")
async def llm_endpoint(request: LLMRequest):
    region = request.region if request.region else "us-east"
    tokens_needed = estimate_tokens(request.prompt)
    model = request.model

    # Select a key based on region, model support, and usage limits.
    key = select_best_key(region, model, tokens_needed)
    print(key)
    if not key:
        raise HTTPException(status_code=429, detail="No available keys; please try again later.")

    # Update usage counters.
    key["current_requests"] += 1
    key["models"][model]["current_tokens"] += tokens_needed

    try:
        # Instantiate the client using the provider configuration from our key.
        # For example, if key["provider"] is "openai", the client should be set up accordingly.
        client = Client(provider_configs=key["provider"])
        
        messages = [{
            "role": "user",
            "content": request.prompt
        }]

        # Measure latency for the API call.
        start_time = time.time()
        result = client.chat.completions.create(
            model=model,
            messages=messages
        )
        latency = time.time() - start_time

        # Update key's average latency metric.
        # For a simple weighted average, if 'avg_latency' exists, combine it with the new value.
        if "avg_latency" in key:
            # Weight the previous average (say, with weight 0.8) and the new latency (0.2)
            key["avg_latency"] = 0.8 * key["avg_latency"] + 0.2 * latency
        else:
            key["avg_latency"] = latency

    except Exception as exc:
        key["health_status"] = "unhealthy"
        raise HTTPException(status_code=500, detail=f"LLM API call failed: {exc}") from exc

    return {"result": result}

