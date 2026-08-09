"""
LLMモデルリスト取得サービス
"""
import httpx

from src.utils.logger import setup_logger

slogger = setup_logger()

class ModelOption:
    """モデルオプション"""
    def __init__(self, value: str, label: str):
        self.value = value
        self.label = label

    def to_dict(self) -> dict[str, str]:
        return {
            "value": self.value,
            "label": self.label
        }


OPENAI_MODELS = [
    ModelOption("gpt-4o-mini", "GPT-4o mini"),
    ModelOption("gpt-4o", "GPT-4o"),
    ModelOption("o3-mini", "o3-mini")
]


async def get_openai_models() -> list[dict[str, str]]:
    """OpenAIのモデルリストを取得"""
    return [model.to_dict() for model in OPENAI_MODELS]


async def get_azure_models() -> list[dict[str, str]]:
    """Azureのモデルリストを取得（OpenAIと同じ）"""
    return [model.to_dict() for model in OPENAI_MODELS]


async def get_openrouter_models() -> list[dict[str, str]]:
    """OpenRouterのモデルリストをAPIから取得"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("https://openrouter.ai/api/v1/models")
            
            if response.status_code != 200:
                slogger.error(f"OpenRouter API error: {response.status_code}")
                return [
                    {"value": "openai/gpt-4o", "label": "OpenAI GPT-4o"},
                    {"value": "anthropic/claude-3-opus", "label": "Anthropic Claude 3 Opus"},
                    {"value": "anthropic/claude-3-sonnet", "label": "Anthropic Claude 3 Sonnet"}
                ]
            
            data = response.json()
            
            if not data or not isinstance(data.get("data"), list):
                slogger.error("Invalid response format from OpenRouter API")
                raise ValueError("Invalid API response format")
            
            return [
                {
                    "value": model.get("id", ""),
                    "label": f"{model.get('provider', 'unknown')} - {model.get('name', model.get('id', 'unknown'))}"
                }
                for model in data["data"]
            ]
    except Exception as e:
        slogger.error(f"Error fetching OpenRouter models: {e}")
        return [
            {"value": "openai/gpt-4o", "label": "OpenAI GPT-4o"},
            {"value": "anthropic/claude-3-opus", "label": "Anthropic Claude 3 Opus"},
            {"value": "anthropic/claude-3-sonnet", "label": "Anthropic Claude 3 Sonnet"}
        ]


async def get_local_llm_models(address: str | None = None) -> list[dict[str, str]]:
    """LocalLLMのモデルリストをAPIから取得"""
    if not address:
        host = "localhost"
        port = 11434  # Ollamaのデフォルトポート
    else:
        try:
            host, port_str = address.split(":")
            port = int(port_str)
        except ValueError:
            slogger.warning(f"Invalid address format: {address}, using default")
            host = "localhost"
            port = 11434
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"http://{host}:{port}/api/models")
            
            if response.status_code != 200:
                slogger.error(f"LocalLLM API error: {response.status_code}")
                return [
                    {"value": "llama3", "label": "Llama 3"},
                    {"value": "mistral", "label": "Mistral"},
                    {"value": "custom", "label": "カスタムモデル"}
                ]
            
            data = response.json()
            
            if not data or not isinstance(data.get("models"), list):
                slogger.error("Invalid response format from LocalLLM API")
                raise ValueError("Invalid API response format")
            
            return [
                {
                    "value": model.get("id", model.get("name", "")),
                    "label": model.get("name", model.get("id", "unknown"))
                }
                for model in data["models"]
            ]
    except Exception as e:
        slogger.error(f"Error fetching LocalLLM models: {e}")
        return [
            {"value": "llama3", "label": "Llama 3"},
            {"value": "mistral", "label": "Mistral"},
            {"value": "custom", "label": "カスタムモデル"}
        ]


async def get_models_by_provider(provider: str, address: str | None = None) -> list[dict[str, str]]:
    """プロバイダーに応じたモデルリストを取得"""
    if provider == "openai":
        return await get_openai_models()
    elif provider == "azure":
        return await get_azure_models()
    elif provider == "openrouter":
        return await get_openrouter_models()
    elif provider == "local":
        return await get_local_llm_models(address)
    else:
        raise ValueError(f"Unknown provider: {provider}")
