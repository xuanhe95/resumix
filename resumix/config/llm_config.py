import os
from dotenv import load_dotenv
from pathlib import Path
from loguru import logger

# Load environment variables
load_dotenv()

class LLMConfig:
    @staticmethod
    def get_config(use_local: bool = False):
        """
        Get LLM configuration based on the mode.
        
        Args:
            use_local (bool): If True, use local LLM configuration
            
        Returns:
            dict: Configuration dictionary for LLM client
        """
        if use_local:
            logger.info("Using local LLM configuration")
            return {
                "url": os.getenv("LOCAL_LLM_URL", "http://localhost:11434/api/generate"),
                "model": os.getenv("LOCAL_LLM_MODEL", "gemma3:4b"),
                "type": "local"
            }
        else:
            logger.info("Using Deepseek API configuration")
            api_key = os.getenv("DEEPSEEK_API_KEY")
            if not api_key:
                raise ValueError("DEEPSEEK_API_KEY not found in environment variables")
                
            return {
                "url": os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions"),
                "api_key": api_key,
                "model": "deepseek-chat",
                "type": "api"
            } 