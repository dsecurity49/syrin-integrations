import unittest
import asyncio
import json
import os
from unittest.mock import MagicMock, AsyncMock, patch
from intent_bus_syrin import IntentBusSyrinHarness, ChiasmObserver, SyrinMissionContext
from intent_bus import ClaimedIntent

class TestSyrinFramework(unittest.TestCase):

    def tearDown(self):
        self.harness.shutdown()

    def setUp(self):
        """Set up dummy objects and mocks before each test."""
        # 1. Mock the Intent Bus Client
        self.mock_bus = MagicMock()
        self.mock_bus.publish = MagicMock()
        self.mock_bus.set = MagicMock()
        self.mock_bus.get = MagicMock()
        self.mock_bus.extend_claim = MagicMock()

        # 2. Mock a basic Agent Factory
        self.mock_agent = MagicMock()
        def dummy_factory():
            return self.mock_agent
        
        # 3. Instantiate the Harness
        self.harness = IntentBusSyrinHarness(
            agent_factory=dummy_factory,
            bus=self.mock_bus,
            mission_timeout=5,
            node_name="test-node"
        )

    def test_error_translation_logic(self):
        """Test that raw HTTP/API tracebacks are correctly translated."""
        
        # Test 500 Server Error
        err_500 = self.harness._translate_error("Server error '500 Internal Server Error' for url")
        self.assertIn("[Upstream Provider Error]", err_500)
        
        # Test 429 Rate Limit
        err_429 = self.harness._translate_error("litellm.exceptions.RateLimitError: 429 Quota Exhausted")
        self.assertIn("[Rate Limit Exceeded]", err_429)
        
        # Test 401 Auth
        err_401 = self.harness._translate_error("Authentication error: invalid api key")
        self.assertIn("[Authentication Failure]", err_401)
        
        # Test Empty Error Fallback
        err_empty = self.harness._translate_error("")
        self.assertEqual(err_empty, "[Unhandled Exception] Unknown Error")

    @patch('urllib.request.urlopen')
    def test_chiasm_observer_http_calls(self, mock_urlopen):
        """Test that the Observer fires the correct POST and PATCH requests."""
        
        # Setup the mock HTTP response for the initial POST (Task Creation)
        mock_response = MagicMock()
        mock_response.status = 201
        mock_response.read.return_value = json.dumps({"id": 99}).encode('utf-8')
        mock_urlopen.return_value.__enter__.return_value = mock_response

        observer = ChiasmObserver(chiasm_url="http://mock-dashboard:4300", api_key="test-key", node_name="test-node")
        
        # Trigger the notification synchronously for testing
        observer._sync_notify("mission_12345", "run_end", {"content": "Hello World"})

        # Assert URL Open was called twice (1 POST to create, 1 PATCH to update)
        self.assertEqual(mock_urlopen.call_count, 2)
        
        # Inspect the PATCH call arguments
        patch_call = mock_urlopen.call_args_list[1][0][0]
        self.assertEqual(patch_call.method, "PATCH")
        self.assertEqual(patch_call.full_url, "http://mock-dashboard:4300/tasks/99")
        
        # Verify the data payload contains the success status
        payload = json.loads(patch_call.data.decode('utf-8'))
        self.assertEqual(payload["status"], "completed")
        self.assertIn("Hello World", payload["summary"])

    def test_mission_context_telemetry(self):
        """Test that the context correctly emits telemetry back to the Intent Bus."""
        
        # FIX: Use MagicMock to mock the SDK object instead of calling __init__
        mock_intent = MagicMock(spec=ClaimedIntent)
        mock_intent.id = "test_mission_001"
        mock_intent.namespace = "default"
        mock_intent.payload = {"instruction": "test", "parent_mission_id": "parent_001"}
        
        ctx = SyrinMissionContext(intent=mock_intent, client=self.mock_bus)
        
        # Run the async telemetry emitter synchronously using asyncio.run
        asyncio.run(ctx.emit_telemetry("tool_call", {"tool": "search"}))
        
        # Verify the bus client published the telemetry intent
        self.mock_bus.publish.assert_called_once()
        publish_kwargs = self.mock_bus.publish.call_args[1]
        
        self.assertEqual(publish_kwargs["goal"], "syrin_trace_tool_call")
        self.assertEqual(publish_kwargs["payload"]["p_id"], "parent_001")
        self.assertEqual(publish_kwargs["payload"]["telemetry"]["tool"], "search")

    def test_json_profile_override(self):
        """Simulate worker.py profile loading logic."""
        import argparse
        
        # Mock CLI args
        args = argparse.Namespace(
            model="gemini/default",
            prompt="Default prompt",
            timeout=900
        )
        
        # Mock JSON Profile data
        profile_data = {
            "model": "gemini/gemini-1.5-pro",
            "timeout": 3600
        }
        
        # Apply logic identical to worker.py
        for key, value in profile_data.items():
            if hasattr(args, key):
                setattr(args, key, value)
                
        # Assert the profile overwrote the defaults, but left unmentioned keys alone
        self.assertEqual(args.model, "gemini/gemini-1.5-pro")
        self.assertEqual(args.timeout, 3600)
        self.assertEqual(args.prompt, "Default prompt")

if __name__ == '__main__':
    unittest.main(verbosity=2)
