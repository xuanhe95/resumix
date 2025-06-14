from typing import Dict, List, Tuple, Union
from abc import ABC, abstractmethod
from sentence_transformers import SentenceTransformer, util
import heapq
from collections import defaultdict
from utils.logger import logger


class BaseParser(ABC):
    def __init__(
        self,
        section_labels: Dict[str, List[str]],
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
        threshold: float = 0.65,
    ):
        self.section_labels = section_labels
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        self.label_embeddings = {
            tag: self.model.encode(labels, convert_to_tensor=True)
            for tag, labels in section_labels.items()
        }

    def normalize_text(self, text: str, keep_blank: bool = False) -> List[str]:
        lines = text.splitlines()
        return [
            line.strip() if keep_blank else line.strip()
            for line in lines
            if keep_blank or line.strip()
        ]

    def vector_classify_line(self, line: str) -> Tuple[Union[str, None], float]:
        if not line.strip():
            return None, 0.0
        line_vec = self.model.encode(line, convert_to_tensor=True)
        best_tag = None
        best_score = -1
        for tag, tag_vecs in self.label_embeddings.items():
            score = util.cos_sim(line_vec, tag_vecs).max().item()
            if score > best_score:
                best_score = score
                best_tag = tag
        return best_tag, best_score

    def is_section_header(self, line: str) -> Tuple[Union[str, None], float]:
        for tag, keywords in self.section_labels.items():
            for kw in keywords:
                if kw.lower() in line.lower():
                    return tag, 1.0
        tag, score = self.vector_classify_line(line)
        return (tag, score) if score >= self.threshold else (None, score)

    def detect_sections(
        self,
        lines: List[str],
        unmatched_break=False,
        unmatched_score=0.2,
        max_unmatched_lines: int = 10,
    ) -> Dict[str, List[str]]:
        tag_heaps: Dict[str, List[Tuple[float, int, str]]] = defaultdict(list)
        for idx, line in enumerate(lines):
            tag, score = self.is_section_header(line)
            if tag:
                heapq.heappush(tag_heaps[tag], (-score, idx))

        if not tag_heaps:
            return {"fallback": lines}

        tag_best: Dict[str, Tuple[float, int]] = {
            tag: (-heap[0][0], heap[0][1]) for tag, heap in tag_heaps.items()
        }

        header_list: List[Tuple[int, str]] = sorted(
            [(idx, tag) for tag, (_, idx) in tag_best.items()]
        )

        section_map: Dict[str, List[str]] = {}

        for i, (start_idx, tag) in enumerate(header_list):
            end_idx = header_list[i + 1][0] if i + 1 < len(header_list) else len(lines)
            section_lines = lines[start_idx:end_idx]

            if unmatched_break:
                # 👇 加入提前终止逻辑
                unmatched_count = 0
                cutoff_idx = len(section_lines)

                for j, line in enumerate(
                    section_lines[1:], start=1
                ):  # skip header line
                    next_tag, next_score = self.is_section_header(line)
                    if not next_tag or next_score < unmatched_score:
                        unmatched_count += 1
                    else:
                        unmatched_count = 0  # 重置

                    if unmatched_count >= max_unmatched_lines:
                        logger.info(
                            f"Cutting off section '{tag}' at line {start_idx + j} due to unmatched lines."
                        )
                        cutoff_idx = j
                        break

            section_map[tag] = section_lines[:cutoff_idx]

        return section_map

    @abstractmethod
    def parse(self, text: str) -> Dict[str, Union[str, List[str]]]:
        pass
