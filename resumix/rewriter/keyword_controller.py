from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sentence_transformers import SentenceTransformer, util
import re


class KeywordController:
    def __init__(self, use_embedding: bool = False):
        self.use_embedding = use_embedding
        self.model = (
            SentenceTransformer("paraphrase-MiniLM-L6-v2") if use_embedding else None
        )

    def extract_keywords(self, text: str, top_k: int = 10) -> List[str]:
        # 简单提取关键词（可以换成 jieba, KeyBERT 等）
        words = re.findall(r"\b\w[\w\-]{1,}\b", text.lower())
        stopwords = {"and", "with", "the", "for", "you", "your", "of", "in", "to"}
        keywords = [w for w in words if w not in stopwords and len(w) > 2]
        return list(dict.fromkeys(keywords))[:top_k]

    def get_positive_keywords(self, jd_text: str) -> List[str]:
        return self.extract_keywords(jd_text)

    def get_negative_keywords(self, section_text: str, jd_text: str) -> List[str]:
        section_keywords = self.extract_keywords(section_text)
        jd_keywords = set(self.extract_keywords(jd_text))

        # 不在 JD 中出现的关键词 → 视为潜在负面关键词
        negative = [kw for kw in section_keywords if kw not in jd_keywords]

        if self.use_embedding:
            # 基于句向量判断是否“不相关”
            section_embs = self.model.encode(section_keywords, convert_to_tensor=True)
            jd_embs = self.model.encode(list(jd_keywords), convert_to_tensor=True)

            # 计算与任一 JD 关键词的最大相似度
            scores = util.cos_sim(section_embs, jd_embs)
            unrelated = []
            for idx, row in enumerate(scores):
                max_sim = row.max().item()
                if max_sim < 0.3:  # 阈值可调
                    unrelated.append(section_keywords[idx])
            return unrelated

        return negative
