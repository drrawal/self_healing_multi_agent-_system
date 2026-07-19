"""
Unit tests for the LLM factory.

These tests verify provider routing logic without making real API calls
by checking the returned class type and constructor arguments.
"""
from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import pytest

from core.agents.llm_factory import build_llm, build_llm_for_provider


def _patch_settings(provider: str, **extra):
    """Return a mock Settings object for a given provider."""
    s = MagicMock()
    s.llm_provider        = provider
    s.llm_model           = "test-model"
    s.llm_temperature     = 0.1
    s.openai_api_key      = "sk-test"
    s.anthropic_api_key   = "sk-ant-test"
    s.azure_openai_endpoint   = "https://test.openai.azure.com/"
    s.azure_openai_api_key    = "azure-key"
    s.azure_openai_deployment = "gpt-4o"
    s.groq_api_key        = "gsk_test"
    s.groq_model          = "llama-3.3-70b-versatile"
    s.ollama_base_url     = "http://localhost:11434"
    s.ollama_model        = "llama3.2"
    for k, v in extra.items():
        setattr(s, k, v)
    return s


# ── Groq ────────────────────────────────────────────────────────────────────

def test_build_llm_groq_returns_chatgroq():
    with patch("core.agents.llm_factory.get_settings", return_value=_patch_settings("groq")):
        # Invalidate lru_cache to pick up patched settings
        build_llm.cache_clear()
        from langchain_groq import ChatGroq
        llm = build_llm()
        assert isinstance(llm, ChatGroq)
        assert llm.model_name == "llama-3.3-70b-versatile"


def test_build_llm_for_provider_groq():
    s = _patch_settings("groq")
    with patch("core.agents.llm_factory.get_settings", return_value=s):
        from langchain_groq import ChatGroq
        llm = build_llm_for_provider("groq", model="llama-3.1-8b-instant")
        assert isinstance(llm, ChatGroq)
        assert llm.model_name == "llama-3.1-8b-instant"


# ── Ollama ──────────────────────────────────────────────────────────────────

def test_build_llm_ollama_returns_chatollama():
    with patch("core.agents.llm_factory.get_settings", return_value=_patch_settings("ollama")):
        build_llm.cache_clear()
        from langchain_ollama import ChatOllama
        llm = build_llm()
        assert isinstance(llm, ChatOllama)
        assert llm.model == "llama3.2"


def test_build_llm_for_provider_ollama_custom_model():
    s = _patch_settings("ollama")
    with patch("core.agents.llm_factory.get_settings", return_value=s):
        from langchain_ollama import ChatOllama
        llm = build_llm_for_provider("ollama", model="mistral")
        assert isinstance(llm, ChatOllama)
        assert llm.model == "mistral"


def test_build_llm_for_provider_ollama_base_url():
    s = _patch_settings("ollama", ollama_base_url="http://remote-host:11434")
    with patch("core.agents.llm_factory.get_settings", return_value=s):
        from langchain_ollama import ChatOllama
        llm = build_llm_for_provider("ollama")
        assert llm.base_url == "http://remote-host:11434"


# ── Unsupported provider ─────────────────────────────────────────────────────

def test_build_llm_unknown_provider_raises():
    with patch("core.agents.llm_factory.get_settings", return_value=_patch_settings("unknown_xyz")):
        build_llm.cache_clear()
        with pytest.raises(ValueError, match="Unsupported LLM provider"):
            build_llm()


def test_build_llm_for_provider_unknown_raises():
    s = _patch_settings("openai")
    with patch("core.agents.llm_factory.get_settings", return_value=s):
        with pytest.raises(ValueError, match="Unsupported provider"):
            build_llm_for_provider("unknown_xyz")


# ── Cleanup ──────────────────────────────────────────────────────────────────

def teardown_module(module):
    """Restore the lru_cache to the real settings after all tests."""
    build_llm.cache_clear()
