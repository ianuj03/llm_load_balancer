import asyncio
import time
from collections import defaultdict

KEY_POOL = {}          # Mapping of model names to lists of keys.
ROUND_ROBIN_INDEX = {} # Mapping of model names to a round-robin counter.
key_lock = asyncio.Lock()  # Global lock for key selection updates.

def init_key_pool(config):
    current_time = time.time()
    for model_name, keys_list in config.get("keys", {}).items():
        KEY_POOL[model_name] = []
        ROUND_ROBIN_INDEX[model_name] = 0
        for key in keys_list:
            key["current_requests"] = 0
            key["health_status"] = "healthy"
            global_window = key.get("global_window", 60)
            key["global_reset_time"] = current_time + global_window

            # Initialize model-specific token counters
            key["current_tokens"] = 0
            key["reset_time"] = current_time + key.get("window", 60)
            KEY_POOL[model_name].append(key)

async def select_best_key(request_region, model, estimated_tokens):
    global ROUND_ROBIN_INDEX
    current_time = time.time()
    candidates = []
    
    # Retrieve keys for the requested model.
    model_keys = KEY_POOL.get(model, [])
    
    # Use the lock to protect reading/updating shared state.
    async with key_lock:
        for key in model_keys:
            # Reset global counters if the window has passed.
            if current_time >= key["global_reset_time"]:
                key["current_requests"] = 0
                key["global_reset_time"] = current_time + key.get("global_window", 60)
                key["health_status"] = "healthy"

            # Skip if key's global rate limit is exceeded.
            if (key["rate_limit"] - key["current_requests"]) < 0:
                continue

            # Reset token counter if window has passed.
            if current_time >= key["reset_time"]:
                key["current_tokens"] = 0
                key["reset_time"] = current_time + key.get("window", 60)

            # Check token capacity.
            if (key["token_limit"] - key["current_tokens"]) >= estimated_tokens:
                candidates.append(key)

        # Filter by region if specified.
        if request_region:
            regional_candidates = [k for k in candidates if k.get("region") == request_region]
        else:
            regional_candidates = candidates

        selected_candidates = regional_candidates if regional_candidates else candidates

        if not selected_candidates:
            return None

        # Sort candidates by avg_latency if available.
        selected_candidates.sort(key=lambda k: k.get("avg_latency", float('inf')))

        # Use a round-robin index specific to this model.
        index = ROUND_ROBIN_INDEX[model] % len(selected_candidates)
        selected_key = selected_candidates[index]
        ROUND_ROBIN_INDEX[model] += 1

        # Record the request for the selected key.
        selected_key["current_requests"] += 1

    # Outside the lock, you might later update token usage as well.
    return selected_key

