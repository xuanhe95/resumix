import json
from typing import Dict, Set


class KeywordsLoader:
    @staticmethod
    def load_keywords(json_path: str) -> Dict[str, Set[str]]:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {category: set(words) for category, words in data.items()}

    @staticmethod
    def flatten_keywords(keyword_dict: Dict[str, Set[str]]) -> Set[str]:
        """合并所有关键词集合"""
        all_keywords = set()
        for words in keyword_dict.values():
            all_keywords.update(words)
        return all_keywords
