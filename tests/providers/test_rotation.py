"""Tests for the multi-key rotation engine (providers/rotation.py)."""

from providers.rotation import RotationConfig


class TestRotationConfig:
    def test_disabled_when_chain_empty(self):
        cfg = RotationConfig("[]", "[]")
        assert cfg.enabled is False

    def test_enabled_when_chain_has_entries(self):
        api_keys = '[{"label": "k1", "api_key": "key1"}]'
        chain = '[{"label": "s1", "model": "gemini/gemini-2.0-flash", "key_label": "k1"}]'
        cfg = RotationConfig(api_keys, chain)
        assert cfg.enabled is True

    def test_resolve_key_found(self):
        cfg = RotationConfig(
            '[{"label": "k1", "api_key": "key1"}, {"label": "k2", "api_key": "key2"}]',
            "[]",
        )
        assert cfg.resolve_key("k1") == "key1"
        assert cfg.resolve_key("k2") == "key2"

    def test_resolve_key_not_found(self):
        cfg = RotationConfig("[]", "[]")
        assert cfg.resolve_key("nonexistent") is None

    def test_skips_step_with_unresolvable_key(self):
        api_keys = '[{"label": "k1", "api_key": "key1"}]'
        chain = (
            "["
            '  {"label": "s1", "model": "gemini/gemini-2.0-flash", "key_label": "bad_key"},'
            '  {"label": "s2", "model": "gemini/gemini-2.5-flash", "key_label": "k1"}'
            "]"
        )
        cfg = RotationConfig(api_keys, chain)
        steps = cfg.steps()
        assert len(steps) == 1
        assert steps[0].label == "s2"
        assert steps[0].api_key == "key1"

    def test_model_id_only_strips_provider_prefix(self):
        cfg = RotationConfig("[]", "[]")
        assert cfg._model_id_only("gemini/gemini-2.0-flash") == "gemini-2.0-flash"
        assert (
            cfg._model_id_only("open_router/anthropic/claude-sonnet-4-20250514")
            == "anthropic/claude-sonnet-4-20250514"
        )

    def test_steps_returns_resolved_entries(self):
        api_keys = (
            '[{"label": "k1", "api_key": "key1"}, {"label": "k2", "api_key": "key2"}]'
        )
        chain = (
            "["
            '  {"label": "s1", "model": "gemini/gemini-2.0-flash", "key_label": "k1"},'
            '  {"label": "s2", "model": "gemini/gemini-2.5-pro", "key_label": "k2"}'
            "]"
        )
        cfg = RotationConfig(api_keys, chain)
        steps = cfg.steps()
        assert len(steps) == 2
        assert steps[0].label == "s1"
        assert steps[0].model == "gemini-2.0-flash"
        assert steps[0].api_key == "key1"
        assert steps[1].label == "s2"
        assert steps[1].model == "gemini-2.5-pro"
        assert steps[1].api_key == "key2"
