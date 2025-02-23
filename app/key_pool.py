import time

KEY_POOL = {}

ROUND_ROBIN_INDEX = 0

def init_key_pool(config):
    current_time = time.time()
    for key in config.get("keys", []):
        key["current_requests"] = 0
        key["health_status"] = "healthy"
        global_window = key.get("global_window", 60)
        key["global_reset_time"] = current_time + global_window

        for model_name, model_params in key.get("models", {}).items():
            model_params["current_tokens"] = 0
            model_params["reset_time"] = current_time + model_params.get("window", 60)
        KEY_POOL[key["api_key"]] = key

def select_best_key(request_region, model, estimated_tokens):
    global ROUND_ROBIN_INDEX
    current_time = time.time()
    candidates = []
    
    for key in KEY_POOL.values():
        # Check if the key supports the requested model.
        if model not in key.get("models", {}):
            continue

        # Reset global counters if the window has passed.
        if current_time >= key["global_reset_time"]:
            key["current_requests"] = 0
            key["global_reset_time"] = current_time + key.get("global_window", 60)
            key["health_status"] = "healthy"

        # Check if the key's global rate limit has been exceeded.
        if (key["rate_limit"] - key["current_requests"]) <= 0:
            continue

        # Model-specific counters.
        model_data = key["models"][model]
        if current_time >= model_data["reset_time"]:
            model_data["current_tokens"] = 0
            model_data["reset_time"] = current_time + model_data.get("window", 60)

        # Check if the key has enough token capacity.
        if (model_data["token_limit"] - model_data["current_tokens"]) >= estimated_tokens:
            candidates.append(key)

    # keys from the requested region for latency
    if request_region:
        regional_candidates = [k for k in candidates if k.get("region") == request_region]
    else:
        regional_candidates = candidates

    selected_candidates = regional_candidates if regional_candidates else candidates

    if not selected_candidates:
        return None

    # round-robin load balancing.
    selected_candidates.sort(key=lambda k: k.get("avg_latency", float('inf')))
    index = ROUND_ROBIN_INDEX % len(selected_candidates)
    selected_key = selected_candidates[index]
    ROUND_ROBIN_INDEX += 1 
    return selected_key

