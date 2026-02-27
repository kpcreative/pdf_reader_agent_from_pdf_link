import os
from dotenv import load_dotenv
from gen_ai_hub.proxy.core.proxy_clients import get_proxy_client
from gen_ai_hub.proxy.native.openai import OpenAI

load_dotenv()

REQUIRED_ENV = [
    "AICORE_AUTH_URL",
    "AICORE_CLIENT_ID",
    "AICORE_CLIENT_SECRET",
    "AICORE_BASE_URL",
    "AICORE_RESOURCE_GROUP",
]

for env in REQUIRED_ENV:
    if not os.getenv(env):
        raise EnvironmentError(f"Missing required environment variable: {env}")

# Model configuration - can be overridden via environment variables
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-5")  # or your preferred model
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")

# Embedding dimensions based on model
EMBEDDING_DIMENSIONS_MAP = {
    "text-embedding-ada-002": 1536,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}
EMBEDDING_DIMENSIONS = EMBEDDING_DIMENSIONS_MAP.get(EMBEDDING_MODEL, 1536)

# Singleton clients
_openai_client = None


def get_llm_client():
    """
    Returns SAP Generative AI Hub OpenAI client.
    """
    global _openai_client
    if _openai_client is None:
        proxy_client = get_proxy_client("gen-ai-hub")
        _openai_client = OpenAI(proxy_client=proxy_client)
        print("✅ Connected to SAP Generative AI Hub (OpenAI)")
    return _openai_client


def get_embeddings(texts: list) -> list:
    """
    Get embeddings using SAP AI Core.
    """
    client = get_llm_client()
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return [item.embedding for item in response.data]


def get_chat_completion(messages: list, tools: list = None):
    """
    Makes a chat completion request via SAP AI Core.
    """
    client = get_llm_client()
    kwargs = {
        "model": MODEL_NAME,
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    
    response = client.chat.completions.create(**kwargs)
    return response