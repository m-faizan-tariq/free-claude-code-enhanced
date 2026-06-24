"""Tests for the multi-key rotation engine (providers/rotation.py)."""

from providers.rotation import RotationConfig


class TestRotationConfig:
    def test_disabled_when_no_keys_and_no_single(self):
        cfg = RotationConfig("[]")
        assert cfg.enabled is False
        assert cfg.next_key() is None

    def test_disabled_when_just_single_key(self):
        cfg = RotationConfig("[]", single_key="key1")
        assert cfg.enabled is False
        assert cfg.next_key() is None

    def test_round_robin_cycles_through_rotation_keys(self):
        api_keys = (
            '[{"label": "k1", "api_key": "key1"}, '
            '{"label": "k2", "api_key": "key2"}]'
        )
        cfg = RotationConfig(api_keys)
        assert cfg.next_key().api_key == "key1"
        assert cfg.next_key().api_key == "key2"
        assert cfg.next_key().api_key == "key1"

    def test_single_key_prepended_when_rotation_list_nonempty(self):
        api_keys = '[{"label": "extra", "api_key": "extra-key"}]'
        cfg = RotationConfig(api_keys, single_key="primary-key")
        assert cfg.enabled is True
        assert cfg.next_key().label == "Primary"
        assert cfg.next_key().api_key == "extra-key"
        assert cfg.next_key().api_key == "primary-key"

    def test_single_key_not_duplicated_if_already_in_list(self):
        api_keys = '[{"label": "k1", "api_key": "dup-key"}]'
        cfg = RotationConfig(api_keys, single_key="dup-key")
        assert cfg.enabled is True
        assert cfg.next_key().api_key == "dup-key"
        # Only one entry in pool
        assert cfg.next_key().api_key == "dup-key"
        assert cfg.next_key().api_key == "dup-key"

    def test_round_robin_single_rotation_key(self):
        api_keys = '[{"label": "k1", "api_key": "key1"}]'
        cfg = RotationConfig(api_keys, single_key="primary")
        assert cfg.enabled is True
        assert cfg.next_key().label == "Primary"
        assert cfg.next_key().api_key == "key1"
