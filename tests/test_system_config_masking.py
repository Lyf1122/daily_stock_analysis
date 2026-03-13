# -*- coding: utf-8 -*-
"""Unit tests for sensitive configuration field masking functionality."""

import os
import tempfile
import unittest
from pathlib import Path

from src.config import Config
from src.core.config_manager import ConfigManager
from src.services.system_config_service import SystemConfigService


class SystemConfigMaskingTestCase(unittest.TestCase):
    """Test cases for verifying sensitive field masking in get_config responses."""

    def setUp(self) -> None:
        """Set up test environment with a temporary .env file."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env_path = Path(self.temp_dir.name) / ".env"
        self.env_path.write_text(
            "\n".join(
                [
                    "STOCK_LIST=600519,000001",
                    "GEMINI_API_KEY=secret-key-value",
                    "OPENAI_API_KEY=sk-test-key-12345",
                    "DASHSCOPE_API_KEY=my-dashscope-key",
                    "SCHEDULE_TIME=18:00",
                    "LOG_LEVEL=INFO",
                    "TELEGRAM_BOT_TOKEN=telegram-token-abc",
                    "TELEGRAM_CHAT_ID=123456789",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        os.environ["ENV_FILE"] = str(self.env_path)
        Config.reset_instance()

        self.manager = ConfigManager(env_path=self.env_path)
        self.service = SystemConfigService(manager=self.manager)

    def tearDown(self) -> None:
        """Clean up test environment."""
        Config.reset_instance()
        os.environ.pop("ENV_FILE", None)
        self.temp_dir.cleanup()

    def test_sensitive_fields_are_masked(self) -> None:
        """Verify that sensitive fields are masked with default mask token."""
        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        # GEMINI_API_KEY should be marked as sensitive in schema and masked
        self.assertIn("GEMINI_API_KEY", items)
        gemini_item = items["GEMINI_API_KEY"]
        self.assertEqual(gemini_item["value"], "******")
        self.assertTrue(gemini_item["is_masked"], "GEMINI_API_KEY should be marked as masked")
        self.assertTrue(gemini_item["raw_value_exists"], "GEMINI_API_KEY should have a raw value")
        self.assertTrue(
            gemini_item["schema"]["is_sensitive"],
            "GEMINI_API_KEY schema should mark is_sensitive=True"
        )

        # OPENAI_API_KEY should be masked
        self.assertIn("OPENAI_API_KEY", items)
        openai_item = items["OPENAI_API_KEY"]
        self.assertEqual(openai_item["value"], "******")
        self.assertTrue(openai_item["is_masked"], "OPENAI_API_KEY should be marked as masked")
        self.assertTrue(
            openai_item["schema"]["is_sensitive"],
            "OPENAI_API_KEY schema should mark is_sensitive=True"
        )

        # DASHSCOPE_API_KEY should be masked
        self.assertIn("DASHSCOPE_API_KEY", items)
        dashscope_item = items["DASHSCOPE_API_KEY"]
        self.assertEqual(dashscope_item["value"], "******")
        self.assertTrue(dashscope_item["is_masked"], "DASHSCOPE_API_KEY should be marked as masked")
        self.assertTrue(
            dashscope_item["schema"]["is_sensitive"],
            "DASHSCOPE_API_KEY schema should mark is_sensitive=True"
        )

        # TELEGRAM_BOT_TOKEN should be masked
        self.assertIn("TELEGRAM_BOT_TOKEN", items)
        telegram_item = items["TELEGRAM_BOT_TOKEN"]
        self.assertEqual(telegram_item["value"], "******")
        self.assertTrue(telegram_item["is_masked"], "TELEGRAM_BOT_TOKEN should be marked as masked")
        self.assertTrue(
            telegram_item["schema"]["is_sensitive"],
            "TELEGRAM_BOT_TOKEN schema should mark is_sensitive=True"
        )

    def test_non_sensitive_fields_keep_value(self) -> None:
        """Verify that non-sensitive fields retain their actual values."""
        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        # STOCK_LIST is not sensitive
        self.assertIn("STOCK_LIST", items)
        stock_item = items["STOCK_LIST"]
        self.assertEqual(stock_item["value"], "600519,000001")
        self.assertFalse(stock_item["is_masked"], "STOCK_LIST should not be masked")
        self.assertFalse(
            stock_item["schema"]["is_sensitive"],
            "STOCK_LIST schema should mark is_sensitive=False"
        )

        # SCHEDULE_TIME is not sensitive
        self.assertIn("SCHEDULE_TIME", items)
        schedule_item = items["SCHEDULE_TIME"]
        self.assertEqual(schedule_item["value"], "18:00")
        self.assertFalse(schedule_item["is_masked"], "SCHEDULE_TIME should not be masked")
        self.assertFalse(
            schedule_item["schema"]["is_sensitive"],
            "SCHEDULE_TIME schema should mark is_sensitive=False"
        )

        # LOG_LEVEL is not sensitive
        self.assertIn("LOG_LEVEL", items)
        log_item = items["LOG_LEVEL"]
        self.assertEqual(log_item["value"], "INFO")
        self.assertFalse(log_item["is_masked"], "LOG_LEVEL should not be masked")
        self.assertFalse(
            log_item["schema"]["is_sensitive"],
            "LOG_LEVEL schema should mark is_sensitive=False"
        )

        # TELEGRAM_CHAT_ID is not sensitive
        self.assertIn("TELEGRAM_CHAT_ID", items)
        chat_id_item = items["TELEGRAM_CHAT_ID"]
        self.assertEqual(chat_id_item["value"], "123456789")
        self.assertFalse(chat_id_item["is_masked"], "TELEGRAM_CHAT_ID should not be masked")
        self.assertFalse(
            chat_id_item["schema"]["is_sensitive"],
            "TELEGRAM_CHAT_ID schema should mark is_sensitive=False"
        )

    def test_mask_token_customizable(self) -> None:
        """Verify that custom mask tokens can be used."""
        custom_mask = "[HIDDEN]"

        payload = self.service.get_config(include_schema=True, mask_token=custom_mask)
        items = {item["key"]: item for item in payload["items"]}

        # Verify the mask_token is reflected in response
        self.assertEqual(payload["mask_token"], custom_mask)

        # GEMINI_API_KEY should use custom mask
        self.assertIn("GEMINI_API_KEY", items)
        gemini_item = items["GEMINI_API_KEY"]
        self.assertEqual(gemini_item["value"], custom_mask)
        self.assertTrue(gemini_item["is_masked"], "GEMINI_API_KEY should be marked as masked")

        # OPENAI_API_KEY should use custom mask
        self.assertIn("OPENAI_API_KEY", items)
        openai_item = items["OPENAI_API_KEY"]
        self.assertEqual(openai_item["value"], custom_mask)
        self.assertTrue(openai_item["is_masked"], "OPENAI_API_KEY should be marked as masked")

        # Non-sensitive fields should still show actual values
        self.assertIn("STOCK_LIST", items)
        stock_item = items["STOCK_LIST"]
        self.assertEqual(stock_item["value"], "600519,000001")
        self.assertFalse(stock_item["is_masked"], "STOCK_LIST should not be masked")

    def test_empty_sensitive_fields_not_masked(self) -> None:
        """Verify that empty sensitive fields are not masked."""
        # Create .env with some sensitive fields not set
        env_content = "\n".join([
            "STOCK_LIST=600519",
            "LOG_LEVEL=INFO",
            # OPENAI_API_KEY not set
        ]) + "\n"
        self.env_path.write_text(env_content, encoding="utf-8")

        payload = self.service.get_config(include_schema=True)
        items = {item["key"]: item for item in payload["items"]}

        # OPENAI_API_KEY should exist but not be masked (no value)
        self.assertIn("OPENAI_API_KEY", items)
        openai_item = items["OPENAI_API_KEY"]
        self.assertEqual(openai_item["value"], "")
        self.assertFalse(openai_item["is_masked"], "Empty OPENAI_API_KEY should not be masked")
        self.assertFalse(openai_item["raw_value_exists"], "OPENAI_API_KEY should not have a raw value")


if __name__ == "__main__":
    unittest.main()
