"""Tests for Kiro (OpenAI-compatible) provider."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from providers.base import ProviderConfig
from providers.kiro import KIRO_DEFAULT_BASE, KiroProvider


class MockMessage:
    def __init__(self, role, content):
        self.role = role
        self.content = content


class MockRequest:
    def __init__(self, **kwargs):
        self.model = "kiro-sonnet"
        self.messages = [MockMessage("user", "Hello")]
        self.max_tokens = 100
        self.temperature = 0.5
        self.top_p = 0.9
        self.system = "System prompt"
        self.stop_sequences = None
        self.tools = []
        self.thinking = MagicMock()
        self.thinking.enabled = True
        for key, value in kwargs.items():
            setattr(self, key, value)


@pytest.fixture
def kiro_config():
    return ProviderConfig(
        api_key="test_kiro_key",
        base_url=KIRO_DEFAULT_BASE,
        rate_limit=10,
        rate_window=60,
        enable_thinking=True,
    )


@pytest.fixture(autouse=True)
def mock_rate_limiter():
    """Mock the global rate limiter to prevent waiting."""

    @asynccontextmanager
    async def _slot():
        yield

    with patch("providers.transports.openai_chat.transport.GlobalRateLimiter") as mock:
        instance = mock.get_scoped_instance.return_value

        async def _passthrough(fn, *args, **kwargs):
            return await fn(*args, **kwargs)

        instance.execute_with_retry = AsyncMock(side_effect=_passthrough)
        instance.concurrency_slot.side_effect = _slot
        yield instance


@pytest.fixture
def kiro_provider(kiro_config):
    return KiroProvider(kiro_config)


def test_init(kiro_config):
    """Test provider initialization."""
    with patch("providers.transports.openai_chat.transport.AsyncOpenAI") as mock_openai:
        provider = KiroProvider(kiro_config)
        assert provider._api_key == "test_kiro_key"
        assert provider._base_url == KIRO_DEFAULT_BASE
        mock_openai.assert_called_once()


def test_default_base_url_constant():
    assert KIRO_DEFAULT_BASE == "http://localhost:8001"


def test_build_request_body_basic(kiro_provider):
    """Basic request body conversion attaches system message from Claude request."""
    req = MockRequest()
    body = kiro_provider._build_request_body(req)

    assert body["model"] == "kiro-sonnet"
    assert body["messages"][0]["role"] == "system"
    assert "max_completion_tokens" in body


def test_build_request_body_global_disable_blocks_reasoning_mapping():
    provider = KiroProvider(
        ProviderConfig(
            api_key="test_kiro_key",
            base_url=KIRO_DEFAULT_BASE,
            rate_limit=10,
            rate_window=60,
            enable_thinking=False,
        )
    )
    req = MockRequest()
    body = provider._build_request_body(req)

    roles = [m.get("role") for m in body.get("messages", [])]
    assert "assistant_reasoning_content" not in roles


def test_build_request_body_preserves_caller_extra_body(kiro_provider):
    req = MockRequest(extra_body={"metadata": {"user": "u1"}})

    body = kiro_provider._build_request_body(req)

    eb = body.get("extra_body")
    assert isinstance(eb, dict)
    assert eb.get("metadata") == {"user": "u1"}


@pytest.mark.asyncio
async def test_stream_response_text(kiro_provider):
    """Text content deltas are emitted as text blocks."""
    req = MockRequest()

    mock_chunk = MagicMock()
    mock_chunk.choices = [
        MagicMock(
            delta=MagicMock(
                content="Hello back!",
                reasoning_content=None,
                tool_calls=None,
            ),
            finish_reason="stop",
        )
    ]
    mock_chunk.usage = MagicMock(completion_tokens=5, prompt_tokens=10)

    async def mock_stream():
        yield mock_chunk

    with patch.object(
        kiro_provider._client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_stream()

        events = [event async for event in kiro_provider.stream_response(req)]

        assert any(
            '"text_delta"' in event and "Hello back!" in event for event in events
        )


@pytest.mark.asyncio
async def test_stream_response_reasoning_content(kiro_provider):
    """reasoning_content deltas are emitted as thinking blocks."""
    req = MockRequest()

    mock_chunk = MagicMock()
    mock_chunk.choices = [
        MagicMock(
            delta=MagicMock(
                content=None,
                reasoning_content="Thinking...",
                tool_calls=None,
            ),
            finish_reason="stop",
        )
    ]
    mock_chunk.usage = MagicMock(completion_tokens=2, prompt_tokens=10)

    async def mock_stream():
        yield mock_chunk

    with patch.object(
        kiro_provider._client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_stream()

        events = [event async for event in kiro_provider.stream_response(req)]

        assert any(
            '"thinking_delta"' in event and "Thinking..." in event for event in events
        )


@pytest.mark.asyncio
async def test_list_model_ids(kiro_provider):
    """Model list is fetched from the kiro-gateway /v1/models endpoint."""
    mock_model = MagicMock()
    mock_model.id = "kiro-sonnet"
    mock_model_list = MagicMock()
    mock_model_list.data = [mock_model]

    with patch.object(
        kiro_provider._client.models, "list", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = mock_model_list
        model_ids = await kiro_provider.list_model_ids()

    assert "kiro-sonnet" in model_ids


@pytest.mark.asyncio
async def test_cleanup(kiro_provider):
    kiro_provider._client = AsyncMock()

    await kiro_provider.cleanup()

    kiro_provider._client.close.assert_called_once()


@pytest.mark.asyncio
async def test_model_list_offline_fallback(kiro_provider):
    """When kiro-gateway is unreachable, list_model_ids raises."""
    with patch.object(
        kiro_provider._client.models, "list", new_callable=AsyncMock
    ) as mock_list:
        mock_list.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(httpx.ConnectError):
            await kiro_provider.list_model_ids()


@pytest.mark.asyncio
async def test_kiro_enabled_false_disables_discovery(kiro_config):
    """KIRO_ENABLED=False prevents model discovery for kiro."""
    settings = MagicMock()
    settings.kiro_enabled = False
    settings.kiro_proxy_api_key = "test_key"

    from providers.registry import _model_list_provider_ids_for_settings

    provider_ids = _model_list_provider_ids_for_settings(settings)
    assert "kiro" not in provider_ids


@pytest.mark.asyncio
async def test_kiro_enabled_true_with_key_enables_discovery(kiro_config):
    """KIRO_ENABLED=True with a non-empty key enables model discovery."""
    settings = MagicMock()
    settings.kiro_enabled = True
    settings.kiro_proxy_api_key = "test_key"
    settings.kiro_base_url = "http://localhost:8001"
    settings.kiro_default_model = "kiro-sonnet"
    settings.kiro_proxy = ""

    from providers.registry import _model_list_provider_ids_for_settings

    provider_ids = _model_list_provider_ids_for_settings(settings)
    assert "kiro" in provider_ids
