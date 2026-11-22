import json
import os
import requests

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "settings.json")


def load_settings():
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    if os.path.exists(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return _defaults()


def _defaults():
    return {
        "ai_provider": "ollama",
        "ollama_url": "http://localhost:11434",
        "ollama_model": "llama3.1",
        "openai_url": "http://localhost:1234/v1",
        "openai_model": "default",
        "openai_api_key": "",
        "anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", ""),
        "anthropic_model": "claude-sonnet-4-20250514",
    }


def save_settings(settings):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)


class AIProvider:
    def chat(self, prompt, system="You are an expert career coach and resume analyst."):
        raise NotImplementedError

    def is_available(self):
        return False

    @property
    def name(self):
        return "Unknown"


class OllamaProvider(AIProvider):
    def __init__(self, base_url="http://localhost:11434", model="llama3.1"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    @property
    def name(self):
        return f"Ollama ({self.model})"

    def is_available(self):
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self):
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                return [m["name"] for m in resp.json().get("models", [])]
        except Exception:
            pass
        return []

    def chat(self, prompt, system="You are an expert career coach and resume analyst."):
        try:
            resp = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                timeout=180,
            )
            if resp.status_code == 200:
                return resp.json()["message"]["content"]
        except Exception:
            pass
        return None


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, base_url="http://localhost:1234/v1", model="default", api_key=""):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    @property
    def name(self):
        return f"OpenAI-compatible ({self.model})"

    def is_available(self):
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.get(f"{self.base_url}/models", headers=headers, timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def chat(self, prompt, system="You are an expert career coach and resume analyst."):
        try:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                },
                timeout=180,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception:
            pass
        return None


class ClaudeProvider(AIProvider):
    def __init__(self, api_key="", model="claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model

    @property
    def name(self):
        return f"Claude ({self.model})"

    def is_available(self):
        return bool(self.api_key)

    def chat(self, prompt, system="You are an expert career coach and resume analyst."):
        if not self.api_key:
            return None
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text
        except Exception:
            return None


def get_provider(settings=None):
    if settings is None:
        settings = load_settings()
    provider_type = settings.get("ai_provider", "ollama")
    if provider_type == "ollama":
        return OllamaProvider(
            base_url=settings.get("ollama_url", "http://localhost:11434"),
            model=settings.get("ollama_model", "llama3.1"),
        )
    elif provider_type == "openai":
        return OpenAICompatibleProvider(
            base_url=settings.get("openai_url", "http://localhost:1234/v1"),
            model=settings.get("openai_model", "default"),
            api_key=settings.get("openai_api_key", ""),
        )
    elif provider_type == "claude":
        return ClaudeProvider(
            api_key=settings.get("anthropic_api_key", os.environ.get("ANTHROPIC_API_KEY", "")),
            model=settings.get("anthropic_model", "claude-sonnet-4-20250514"),
        )
    return OllamaProvider()
