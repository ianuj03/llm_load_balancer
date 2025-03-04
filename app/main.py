import asyncio
from fastapi import FastAPI
from app.config import load_config
from app.key_pool import init_key_pool
from app.urls_views import router as llm_router
from app.healthy import health_check_worker

app = FastAPI()

# Load configuration (from local file or S3 based on CONFIG_PATH)
config = load_config()
init_key_pool(config)

# Register the API endpoints.
app.include_router(llm_router)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(health_check_worker())

