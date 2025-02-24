import asyncio
import time
from .key_pool import KEY_POOL

async def health_check_worker():
    """
    Background task that periodically resets usage counters for each key.
    KEY_POOL is assumed to be a dictionary mapping model names to lists of keys.
    Each key has:
      - Global usage counters (current_requests, global_reset_time)
      - A nested 'models' dictionary containing model-specific counters:
           current_tokens and reset_time for each model.
    """
    while True:
        await asyncio.sleep(10)
        current_time = time.time()
        # Iterate over each model's list of keys in the key pool.
        for model_keys in KEY_POOL.values():
            for key in model_keys:
                # Reset global counters if the global window has elapsed.
                if current_time >= key["global_reset_time"]:
                    key["current_requests"] = 0
                    key["global_reset_time"] = current_time + key.get("global_window", 60)
                    key["health_status"] = "healthy"

                # Reset model-specific token counters if the window has elapsed.
                # Here we assume each key has a nested "models" dictionary.
                for model_name, model_data in key.get("models", {}).items():
                    if current_time >= model_data["reset_time"]:
                        model_data["current_tokens"] = 0
                        model_data["reset_time"] = current_time + model_data.get("window", 60)

