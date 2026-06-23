"""Tests for multi-key rotation settings in config/settings.py."""

import json

import pytest
from pydantic import ValidationError

from config.settings import Settings


class TestGeminiMultiKeySettings:
    def test_gemini_api_keys_roundtrip(self, monkeypatch):
        keys_json = json.dumps([
            {"label": "Project A", "api_key": "AIza-test-key-a"},
            {"label": "Project B", "api_key": "AIza-test-key-b"},
        ])
        monkeypatch.setenv("GEMINI_API_KEYS", keys_json)
        settings = Settings()
        parsed = json.loads(settings.gemini_api_keys)
        assert parsed == [
            {"label": "Project A", "api_key": "AIza-test-key-a"},
            {"label": "Project B", "api_key": "AIza-test-key-b"},
        ]

    def test_gemini_fallback_chain_roundtrip(self, monkeypatch):
        chain_json = json.dumps([
            {
                "label": "Primary",
                "model": "gemini/models/gemini-3.1-flash-lite",
                "key_label": "__default__",
            },
            {
                "label": "Backup A",
                "model": "gemini/models/gemini-3.1-flash-lite",
                "key_label": "Project A",
            },
        ])
        monkeypatch.setenv("GEMINI_FALLBACK_CHAIN", chain_json)
        settings = Settings()
        parsed = json.loads(settings.gemini_fallback_chain)
        assert parsed == [
            {
                "label": "Primary",
                "model": "gemini/models/gemini-3.1-flash-lite",
                "key_label": "__default__",
            },
            {
                "label": "Backup A",
                "model": "gemini/models/gemini-3.1-flash-lite",
                "key_label": "Project A",
            },
        ]

    def test_missing_gemini_api_keys_fallback_no_error(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEYS", raising=False)
        monkeypatch.delenv("GEMINI_FALLBACK_CHAIN", raising=False)
        settings = Settings()
        assert json.loads(settings.gemini_api_keys) == []
        assert json.loads(settings.gemini_fallback_chain) == []

    def test_invalid_json_gemini_api_keys_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", "not-valid-json")
        with pytest.raises(ValidationError):
            Settings()

    def test_invalid_json_gemini_fallback_chain_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_FALLBACK_CHAIN", "{bad json}")
        with pytest.raises(ValidationError):
            Settings()

    def test_gemini_api_keys_missing_label_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", json.dumps([{"api_key": "test"}]))
        with pytest.raises(ValidationError):
            Settings()

    def test_gemini_api_keys_missing_api_key_raises(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEYS", json.dumps([{"label": "Test"}]))
        with pytest.raises(ValidationError):
            Settings()


class TestOpenRouterMultiKeySettings:
    def test_openrouter_api_keys_roundtrip(self, monkeypatch):
        keys_json = json.dumps([
            {"label": "Account 1", "api_key": "sk-or-v1-test-key"},
        ])
        monkeypatch.setenv("OPENROUTER_API_KEYS", keys_json)
        settings = Settings()
        parsed = json.loads(settings.openrouter_api_keys)
        assert parsed == [{"label": "Account 1", "api_key": "sk-or-v1-test-key"}]

    def test_openrouter_fallback_chain_roundtrip(self, monkeypatch):
        chain_json = json.dumps([
            {
                "label": "Primary",
                "model": "open_router/models/test-model",
                "key_label": "__default__",
            },
        ])
        monkeypatch.setenv("OPENROUTER_FALLBACK_CHAIN", chain_json)
        settings = Settings()
        parsed = json.loads(settings.openrouter_fallback_chain)
        assert parsed == [
            {
                "label": "Primary",
                "model": "open_router/models/test-model",
                "key_label": "__default__",
            },
        ]

    def test_missing_openrouter_api_keys_fallback_no_error(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEYS", raising=False)
        monkeypatch.delenv("OPENROUTER_FALLBACK_CHAIN", raising=False)
        settings = Settings()
        assert json.loads(settings.openrouter_api_keys) == []
        assert json.loads(settings.openrouter_fallback_chain) == []

    def test_invalid_json_openrouter_settings_raises(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEYS", "bad json")
        with pytest.raises(ValidationError):
            Settings()

    def test_openrouter_api_keys_empty_label_raises(self, monkeypatch):
        monkeypatch.setenv(
            "OPENROUTER_API_KEYS",
            json.dumps([{"label": "", "api_key": "sk-or-v1-test"}]),
        )
        with pytest.raises(ValidationError):
            Settings()
