import time

KEY_POOL = {}

ROUND_ROBIN_INDEX = {}

def init_key_pool(config):
    current_time = time.time()
    # config["keys"] is now a dictionary where each key is a model name
    for model_name, keys_list in config.get("keys", {}).items():
        KEY_POOL[model_name] = []
        ROUND_ROBIN_INDEX[model_name] = 0
        for key in keys_list:
            key["current_requests"] = 0
            key["health_status"] = "healthy"
            global_window = key.get("global_window", 60)
            key["global_reset_time"] = current_time + global_window

            # Here we assume the key has top-level token limit and window values.
            key["current_tokens"] = 0
            key["reset_time"] = current_time + key.get("window", 60)
            KEY_POOL[model_name].append(key)


def select_best_key(request_region, model, estimated_tokens):
    current_time = time.time()
    # Retrieve keys for the requested model.
    model_keys = KEY_POOL.get(model, [])
    candidates = []
    
    for key in model_keys:
        # Reset global counters if the window has passed.
        if current_time >= key["global_reset_time"]:
            key["current_requests"] = 0
            key["global_reset_time"] = current_time + key.get("global_window", 60)
            key["health_status"] = "healthy"

        # Skip if the key's global rate limit is exceeded.
        if (key["rate_limit"] - key["current_requests"]) <= 0:
            continue

        # Reset model-specific tokens if the window has passed.
        if current_time >= key["reset_time"]:
            key["current_tokens"] = 0
            key["reset_time"] = current_time + key.get("window", 60)

        # Check if the key has enough token capacity.
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

    # Sort candidates by their average latency (if available) so that lower latency keys are prioritized.
    selected_candidates.sort(key=lambda k: k.get("avg_latency", float('inf')))

    # Use a round-robin index specific to this model.
    index = ROUND_ROBIN_INDEX[model] % len(selected_candidates)
    selected_key = selected_candidates[index]
    ROUND_ROBIN_INDEX[model] += 1

    return selected_key

