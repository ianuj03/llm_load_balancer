## Load Balancer for LLM

#### Installation
`pip3 install -r requirements.txt`

#### Starting up
`uvicorn app.main:app --reload`

#### Request
`curl -X POST "http://localhost:8000/api/llm" \
-H "Content-Type: application/json" \
-d '{"prompt": "How to be more active?", "region": "us-east", "model": "openai:gpt-4o"}'
`
