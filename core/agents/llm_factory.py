"""
LLM factory – single place to create ChatModel instances.
Supports OpenAI, Anthropic, Azure OpenAI, Groq, and Ollama.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from config.settings import get_settings


@lru_cache(maxsize=4)
def build_llm(temperature: float | None = None) -> BaseChatModel:
    """
    Return a cached ChatModel for the configured provider.
    ``temperature`` overrides the settings value (useful for test stubs).

    Supported providers
    -------------------
    openai       – OpenAI API  (gpt-4o, gpt-4o-mini, …)
    anthropic    – Anthropic   (claude-3-5-sonnet, …)
    azure_openai – Azure OpenAI deployment
    groq         – Groq cloud  (llama-3.3-70b-versatile, mixtral-8x7b, …)
    ollama       – Local Ollama server (llama3.2, mistral, …)
    """
    settings = get_settings()
    temp     = temperature if temperature is not None else settings.llm_temperature

    if settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model       = settings.llm_model,
            temperature = temp,
            api_key     = settings.openai_api_key,
        )

    if settings.llm_provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model       = settings.llm_model,
            temperature = temp,
            api_key     = settings.anthropic_api_key,
        )

    if settings.llm_provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI
        return AzureChatOpenAI(
            azure_endpoint   = settings.azure_openai_endpoint,
            api_key          = settings.azure_openai_api_key,
            azure_deployment = settings.azure_openai_deployment,
            temperature      = temp,
        )

    if settings.llm_provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model       = settings.groq_model,
            temperature = temp,
            api_key     = settings.groq_api_key,
        )

    if settings.llm_provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model       = settings.ollama_model,
            temperature = temp,
            base_url    = settings.ollama_base_url,
        )

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider!r}")


def build_llm_for_provider(
    provider   : str,
    model      : str | None = None,
    temperature: float | None = None,
) -> BaseChatModel:
    """
    Build a ChatModel for an explicit provider/model pair without
    touching the cached singleton.  Useful for multi-provider experiments.
    """
    settings = get_settings()
    temp     = temperature if temperature is not None else settings.llm_temperature

    if provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model       = model or settings.groq_model,
            temperature = temp,
            api_key     = settings.groq_api_key,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model       = model or settings.ollama_model,
            temperature = temp,
            base_url    = settings.ollama_base_url,
        )

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model       = model or settings.llm_model,
            temperature = temp,
            api_key     = settings.openai_api_key,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model       = model or settings.llm_model,
            temperature = temp,
            api_key     = settings.anthropic_api_key,
        )

    raise ValueError(f"Unsupported provider: {provider!r}")
