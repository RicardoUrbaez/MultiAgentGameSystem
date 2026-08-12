import importlib
import os
import unittest
from unittest import mock

from game_builder import agent


class ModelProviderTests(unittest.TestCase):
    def test_model_mapping_is_gemini_only(self):
        for runtime_agent in agent.runtime_agents:
            self.assertEqual(
                agent.get_model_for_agent(runtime_agent.name),
                agent.GEMINI_MODEL,
            )
            self.assertTrue(agent.uses_google_model(runtime_agent.name))

    def test_old_openai_environment_does_not_change_agent_models(self):
        original_provider = os.environ.get("MODEL_PROVIDER")
        original_key = os.environ.get("OPENAI_API_KEY")
        try:
            with mock.patch.dict(
                os.environ,
                {
                    "MODEL_PROVIDER": "openai",
                    "OPENAI_API_KEY": "test-key",
                },
                clear=False,
            ):
                configured = importlib.reload(agent)
                self.assertEqual(len(configured.runtime_agents), 5)
                for runtime_agent in configured.runtime_agents:
                    self.assertEqual(runtime_agent.model, configured.GEMINI_MODEL)
        finally:
            if original_provider is None:
                os.environ.pop("MODEL_PROVIDER", None)
            else:
                os.environ["MODEL_PROVIDER"] = original_provider
            if original_key is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = original_key
            importlib.reload(agent)


if __name__ == "__main__":
    unittest.main()
