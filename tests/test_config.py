"""Tests for config module — masking, keys, save/reload."""

import os
import tempfile
from pathlib import Path

import pytest

from ask.config import (
    CONFIG_LABELS,
    GENERAL_KEYS,
    PROVIDER_KEYS,
    SECRET_KEYS,
    Config,
    mask_secret,
)


class TestMaskSecret:
    def test_none(self):
        assert mask_secret(None) == "(not set)"

    def test_empty(self):
        assert mask_secret("") == "(not set)"

    def test_short_key(self):
        result = mask_secret("abc")
        assert result == "***"

    def test_medium_key(self):
        result = mask_secret("abcdef")
        assert result == "******"

    def test_long_key(self):
        result = mask_secret("sk-1234567890abcdef")
        # First 3 + masked middle + last 3
        assert result.startswith("sk-")
        assert result.endswith("def")
        assert "*" in result
        assert len(result) == len("sk-1234567890abcdef")

    def test_exact_seven_chars(self):
        result = mask_secret("abcdefg")
        assert result.startswith("abc")
        assert result.endswith("efg")
        assert "*" in result


class TestSecretKeys:
    def test_openai_is_secret(self):
        assert "OPENAI_API_KEY" in SECRET_KEYS

    def test_gemini_is_secret(self):
        assert "GEMINI_API_KEY" in SECRET_KEYS

    def test_azure_is_secret(self):
        assert "AZURE_OPENAI_API_KEY" in SECRET_KEYS

    def test_model_is_not_secret(self):
        assert "OPENAI_MODEL" not in SECRET_KEYS

    def test_provider_is_not_secret(self):
        assert "LLM_PROVIDER" not in SECRET_KEYS


class TestProviderKeys:
    def test_openai_keys(self):
        keys = PROVIDER_KEYS["openai"]
        assert "OPENAI_API_KEY" in keys
        assert "OPENAI_MODEL" in keys

    def test_ollama_keys(self):
        keys = PROVIDER_KEYS["ollama"]
        assert "OLLAMA_BASE_URL" in keys
        assert "OLLAMA_MODEL" in keys

    def test_gemini_keys(self):
        keys = PROVIDER_KEYS["gemini"]
        assert "GEMINI_API_KEY" in keys
        assert "GEMINI_MODEL" in keys

    def test_azure_keys(self):
        keys = PROVIDER_KEYS["azure_openai"]
        assert "AZURE_OPENAI_ACCOUNT_NAME" in keys
        assert "AZURE_OPENAI_API_KEY" in keys
        assert "AZURE_OPENAI_DEPLOYMENT" in keys
        assert "AZURE_OPENAI_API_VERSION" in keys

    def test_local_keys_empty(self):
        assert PROVIDER_KEYS["local"] == []


class TestGeneralKeys:
    def test_contains_max_commands(self):
        assert "MAX_COMMANDS" in GENERAL_KEYS

    def test_contains_history_size(self):
        assert "HISTORY_SIZE" in GENERAL_KEYS


class TestConfigLabels:
    def test_every_known_key_has_label(self):
        all_keys = set()
        all_keys.add("LLM_PROVIDER")
        for provider_keys in PROVIDER_KEYS.values():
            all_keys.update(provider_keys)
        all_keys.update(GENERAL_KEYS)
        for key in all_keys:
            assert key in CONFIG_LABELS, f"Missing label for {key}"


class TestConfigSaveReload:
    def test_set_val_and_reload(self, tmp_path):
        config_file = tmp_path / ".askrc"
        config_file.write_text("LLM_PROVIDER=local\n", encoding="utf-8")

        cfg = Config.__new__(Config)
        cfg.config_path = config_file
        cfg.vals = {"LLM_PROVIDER": "local"}

        cfg.set_val("MAX_COMMANDS", "5")
        assert cfg.vals["MAX_COMMANDS"] == "5"

        # Reload and verify it persisted
        cfg.reload()
        assert cfg.vals.get("MAX_COMMANDS") == "5"
        assert cfg.vals.get("LLM_PROVIDER") == "local"

    def test_save_writes_file(self, tmp_path):
        config_file = tmp_path / ".askrc"
        config_file.write_text("", encoding="utf-8")

        cfg = Config.__new__(Config)
        cfg.config_path = config_file
        cfg.vals = {"LLM_PROVIDER": "openai", "OPENAI_API_KEY": "sk-test123"}

        cfg.save()

        content = config_file.read_text(encoding="utf-8")
        assert "LLM_PROVIDER=openai" in content
        assert "OPENAI_API_KEY=sk-test123" in content


class TestConfigDefaults:
    def test_max_commands_default(self, tmp_path):
        config_file = tmp_path / ".askrc"
        config_file.write_text("LLM_PROVIDER=local\n", encoding="utf-8")

        cfg = Config.__new__(Config)
        cfg.config_path = config_file
        cfg.vals = {"LLM_PROVIDER": "local"}

        assert cfg.max_commands == "3"

    def test_history_size_default(self, tmp_path):
        config_file = tmp_path / ".askrc"
        config_file.write_text("LLM_PROVIDER=local\n", encoding="utf-8")

        cfg = Config.__new__(Config)
        cfg.config_path = config_file
        cfg.vals = {"LLM_PROVIDER": "local"}

        assert cfg.history_size == "100"

    def test_max_commands_custom(self, tmp_path):
        config_file = tmp_path / ".askrc"
        config_file.write_text("LLM_PROVIDER=local\nMAX_COMMANDS=5\n", encoding="utf-8")

        cfg = Config.__new__(Config)
        cfg.config_path = config_file
        cfg.vals = {"LLM_PROVIDER": "local", "MAX_COMMANDS": "5"}

        assert cfg.max_commands == "5"
