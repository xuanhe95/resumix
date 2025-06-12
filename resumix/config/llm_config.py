import os
from dotenv import load_dotenv
from pathlib import Path
from utils.logger import logger
from config.config import Config


CONFIG = Config().config

# Load environment variables
load_dotenv()


class LLMConfig:
    @staticmethod
    def get_config():
        """
        Get LLM configuration based on the mode.

        Args:
            use_local (bool): If True, use local LLM configuration

        Returns:
            dict: Configuration dictionary for LLM client
        """

        if CONFIG.LLM.USE_MODEL == "local":
            logger.info("Using local LLM configuration")
            return {
                "url": CONFIG.LLM.LOCAL.URL,
                "model": os.getenv("LOCAL_LLM_MODEL", "gemma3:4b"),
                "type": "local",
            }
        elif CONFIG.LLM.USE_MODEL == "deepseek":
            logger.info("Using Deepseek API configuration")
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY not found in environment variables")

            return {
                "url": CONFIG.LLM.DEEPSEEK.URL,
                "api_key": api_key,
                "model": "deepseek-chat",
                "type": "deepseek",
            }
        elif CONFIG.LLM.USE_MODEL == "silicon":
            logger.info("Using Silicon API configuration")
            api_key = os.getenv("SILICON_API_KEY")
            if not api_key:
                raise ValueError("SILICON_API_KEY not found in environment variables")

            return {
                "url": CONFIG.LLM.SILICON.URL,
                "api_key": api_key,
                "model": CONFIG.LLM.SILICON.MODEL,
                "type": "silicon",
            }
        elif CONFIG.LLM.USE_MODEL == "teleai":
            logger.info("Using TeleAI API configuration")
            api_key = os.getenv("TELEAI_API_KEY")
            if not api_key:
                raise ValueError("TELEAI_API_KEY not found in environment variables")

            return {
                "url": os.getenv(
                    "TELEAI_API_URL", "https://api.teleai.com/v1/chat/completions"
                ),
                "username": os.getenv("TELEAI_USERNAME", ""),
                "api_key": api_key,
                "type": "teleai",
            }
