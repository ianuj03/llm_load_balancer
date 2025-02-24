import asyncio
import time
from app.lock_key import key_update_lock
from collections import defaultdict

KEY_POOL = {}          # Mapping of model names to lists of keys.
ROUND_ROBIN_INDEX = {} # Mapping of model names to a round-robin counter.

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


async def select_best_key(model, estimated_tokens):
    global ROUND_ROBIN_INDEX
    current_time = time.time()
    candidates = []
    
    async with key_update_lock:
        model_keys = KEY_POOL.get(model, [])
        for key in model_keys:
            # Reset if the window has passed.
            if current_time >= key["global_reset_time"]:
                key["current_requests"] = 0
                key["global_reset_time"] = current_time + key.get("global_window", 60)
                key["health_status"] = "healthy"
            
            if (key["rate_limit"] - key["current_requests"]) <= 0:
                continue
            
            if current_time >= key["reset_time"]:
                key["current_tokens"] = 0
                key["reset_time"] = current_time + key.get("window", 60)
            
            if (key["token_limit"] - key["current_tokens"]) >= estimated_tokens:
                candidates.append(key)
        
        if not candidates:
            return None
        
        candidates.sort(key=lambda k: k.get("avg_latency", float('inf')))
        
        index = ROUND_ROBIN_INDEX[model] % len(candidates)
        selected_key = candidates[index]
        ROUND_ROBIN_INDEX[model] += 1

    return selected_key

