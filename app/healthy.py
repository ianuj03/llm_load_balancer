import asyncio
import time
from .key_pool import KEY_POOL

async def health_check_worker():
    while True:
        await asyncio.sleep(10)
        current_time = time.time()
        for key in KEY_POOL.values():
            if current_time >= key["global_reset_time"]:
                key["current_requests"] = 0
                key["global_reset_time"] = current_time + key.get("global_window", 60)
                key["health_status"] = "healthy"

            for model_name, model_data in key.get("models", {}).items():
                if current_time >= model_data["reset_time"]:
                    model_data["current_tokens"] = 0
                    model_data["reset_time"] = current_time + model_data.get("window", 60)

