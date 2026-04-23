"""pytest fixtures for adapter tests."""
import json
import pytest


@pytest.fixture
def oai_mock(httpserver):
    """Mock OpenAI-compatible /v1/chat/completions endpoint.

    Usage:
        def test_x(oai_mock):
            oai_mock.respond_with_decision("deny")
            # ...run adapter pointed at oai_mock.url...
    """
    class MockController:
        def __init__(self, server):
            self.server = server
            self.url = server.url_for("/v1")

        def respond_with_decision(self, decision, status=200, extra_body=None):
            body = {
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": json.dumps({"decision": decision}),
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
            if extra_body:
                body.update(extra_body)
            self.server.expect_request(
                "/v1/chat/completions", method="POST"
            ).respond_with_json(body, status=status)

        def respond_with_raw_content(self, content, status=200):
            body = {
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
            }
            self.server.expect_request(
                "/v1/chat/completions", method="POST"
            ).respond_with_json(body, status=status)

    return MockController(httpserver)
