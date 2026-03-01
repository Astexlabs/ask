from pathlib import Path
from typing import Dict, Optional

from dotenv import dotenv_values


# Keys that hold secret values — never shown in plain text in the TUI
SECRET_KEYS = frozenset({
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "AZURE_OPENAI_API_KEY",
})

# Human-readable labels for every config key the TUI knows about
CONFIG_LABELS: Dict[str, str] = {
    "LLM_PROVIDER": "LLM Provider",
    "OPENAI_API_KEY": "OpenAI API Key",
    "OPENAI_MODEL": "OpenAI Model",
    "OLLAMA_BASE_URL": "Ollama Base URL",
    "OLLAMA_MODEL": "Ollama Model",
    "GEMINI_API_KEY": "Gemini API Key",
    "GEMINI_MODEL": "Gemini Model",
    "AZURE_OPENAI_ACCOUNT_NAME": "Azure Account Name",
    "AZURE_OPENAI_API_KEY": "Azure API Key",
    "AZURE_OPENAI_DEPLOYMENT": "Azure Deployment",
    "AZURE_OPENAI_API_VERSION": "Azure API Version",
    "MAX_COMMANDS": "Max Commands Per Query",
    "HISTORY_SIZE": "History Size (entries)",
}

# Which keys are relevant for each provider
PROVIDER_KEYS: Dict[str, list] = {
    "openai": ["OPENAI_API_KEY", "OPENAI_MODEL"],
    "ollama": ["OLLAMA_BASE_URL", "OLLAMA_MODEL"],
    "gemini": ["GEMINI_API_KEY", "GEMINI_MODEL"],
    "azure_openai": [
        "AZURE_OPENAI_ACCOUNT_NAME",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_API_VERSION",
    ],
    "local": [],
}

GENERAL_KEYS = ["MAX_COMMANDS", "HISTORY_SIZE"]


def mask_secret(value: Optional[str]) -> str:
    """Return a masked representation of a secret value."""
    if not value:
        return "(not set)"
    if len(value) <= 6:
        return "*" * len(value)
    return value[:3] + "*" * (len(value) - 6) + value[-3:]


class Config:
    def __init__(self):
        self.config_path = Path.home() / ".askrc"
        self.vals = dotenv_values(self.config_path)

    def reload(self):
        """Re-read the config file from disk."""
        self.vals = dotenv_values(self.config_path)

    def save(self) -> None:
        """Write current vals back to the config file."""
        lines = []
        for key, value in self.vals.items():
            if value is not None:
                lines.append(f"{key}={value}\n")
        with open(self.config_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def set_val(self, key: str, value: str) -> None:
        """Update a single config value and persist to disk."""
        self.vals[key] = value
        self.save()

    @property
    def llm_provider(self):
        return self.vals.get("LLM_PROVIDER")

    # OpenAI
    @property
    def openai_api_key(self):
        return self.vals.get("OPENAI_API_KEY")

    @property
    def openai_model(self):
        return self.vals.get("OPENAI_MODEL")

    # Ollama
    @property
    def ollama_base_url(self):
        return self.vals.get("OLLAMA_BASE_URL")

    @property
    def ollama_model(self):
        return self.vals.get("OLLAMA_MODEL")

    # Gemini
    @property
    def gemini_model(self):
        return self.vals.get("GEMINI_MODEL")

    @property
    def gemini_api_key(self):
        return self.vals.get("GEMINI_API_KEY")

    # Azure OpenAI
    @property
    def azure_openai_account_name(self):
        return self.vals.get("AZURE_OPENAI_ACCOUNT_NAME")

    @property
    def azure_openai_api_key(self):
        return self.vals.get("AZURE_OPENAI_API_KEY")

    @property
    def azure_openai_deployment(self):
        return self.vals.get("AZURE_OPENAI_DEPLOYMENT")

    @property
    def azure_openai_api_version(self):
        return self.vals.get("AZURE_OPENAI_API_VERSION")

    # General settings
    @property
    def max_commands(self):
        return self.vals.get("MAX_COMMANDS", "3")

    @property
    def history_size(self):
        return self.vals.get("HISTORY_SIZE", "100")


config = Config()
