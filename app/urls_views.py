import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .key_pool import select_best_key
from .utils import estimate_tokens
from aisuite.client import Client
from app.lock_key import key_update_lock  # Import our global lock

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

    key = await select_best_key(model, tokens_needed) # region, 
    print(key)
    if not key:
        raise HTTPException(status_code=429, detail="No available keys; please try again later.")
    # Update usage counters inside a lock to avoid race conditions.
    async with key_update_lock: 
        key["current_requests"] += 1
        key["current_tokens"] += tokens_needed

    try:
        # Instantiate the client using the provider configuration from our key.
        client = Client(provider_configs=key["provider"])
        
        messages = [{
            "role": "user",
            "content": request.prompt
        }]

        result = {"message": "Bypassed call"}

        '''

        # Measure latency for the API call.
        start_time = time.time()
        result = client.chat.completions.create(
            model=model,
            messages=messages
        )
        latency = time.time() - start_time

        # Assuming result.usage contains token usage details.
        actual_prompt_tokens = result.usage.prompt_tokens
        actual_completion_tokens = result.usage.completion_tokens
        actual_total_tokens = result.usage.total_tokens

        # Update key's token counter based on actual usage.
        async with key_update_lock:
            # We already added tokens_needed before, so add the difference.
            key["current_tokens"] += actual_total_tokens - tokens_needed 

            # Update key's average latency metric.
            if "avg_latency" in key:
                key["avg_latency"] = 0.8 * key["avg_latency"] + 0.2 * latency
            else:
                key["avg_latency"] = latency
        '''

    except Exception as exc:
        async with key_update_lock:
            key["health_status"] = "unhealthy"
        raise HTTPException(status_code=500, detail=f"LLM API call failed: {exc}") from exc

    return {"result": result}

