from ask.config import config
from ask.constants import LLMProviders
from ask.llms.inference_provider_base import InferenceProvider


def get_inference_provider() -> InferenceProvider:
    if config.llm_provider == LLMProviders.OPENAI:
        # pylint: disable=import-outside-toplevel
        from ask.llms.openai.provider import OpenAIProvider

        return OpenAIProvider()
    elif config.llm_provider == LLMProviders.OLLAMA:
        # pylint: disable=import-outside-toplevel
        from ask.llms.ollama.provider import OllamaProvider

        return OllamaProvider()
    elif config.llm_provider == LLMProviders.GEMINI:
        # pylint: disable=import-outside-toplevel
        from ask.llms.gemini.provider import GeminiProvider

        return GeminiProvider()
    elif config.llm_provider == LLMProviders.AZURE_OPENAI:
        # pylint: disable=import-outside-toplevel
        from ask.llms.azure_openai.provider import AzureOpenAIProvider

        return AzureOpenAIProvider()
    elif config.llm_provider == LLMProviders.LOCAL:
        # pylint: disable=import-outside-toplevel
        from ask.llms.local.provider import LocalProvider

        return LocalProvider()
    else:
        raise ValueError(f"Invalid LLM provider: {config.llm_provider}")
