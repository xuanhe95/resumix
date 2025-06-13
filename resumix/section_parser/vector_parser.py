from typing import Dict, List, Tuple, Union
from sentence_transformers import SentenceTransformer, util
import os
import sys
import heapq
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from resumix.utils.logger import logger

from resumix.section_parser.section_labels import SectionLabels

from resumix.section.education_section import EducationSection
from resumix.section.experience_section import ExperienceSection
from resumix.section.info_section import PersonalInfoSection
from resumix.section.projects_section import ProjectsSection
from resumix.section.skills_section import SkillsSection
from resumix.section.section_base import SectionBase
from resumix.utils.timeit import timeit

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

SECTION_BASE = {
    "personal_info": PersonalInfoSection,
    "education": EducationSection,
    "experience": ExperienceSection,
    "projects": ProjectsSection,
    "skills": SkillsSection,
}

SECTION_LABELS = SectionLabels.get_labels()


class VectorParser:
    def __init__(
        self, model_name="paraphrase-multilingual-MiniLM-L12-v2", threshold=0.65
    ):
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        # 这里可以改为持久化设置
        self.LABEL_EMBEDDINGS = {
            tag: self.model.encode(labels, convert_to_tensor=True)
            for tag, labels in SECTION_LABELS.items()
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
        for tag, tag_vecs in self.LABEL_EMBEDDINGS.items():
            # 计算行向量与标签向量的相似度，提取最大值
            score = util.cos_sim(line_vec, tag_vecs).max().item()
            if score > best_score:
                best_score = score
                best_tag = tag
        return best_tag, best_score

    def is_section_header(self, line: str) -> Tuple[Union[str, None], float]:
        # 1. 关键词匹配优先
        for tag, keywords in SECTION_LABELS.items():
            for kw in keywords:
                if kw.lower() in line.lower():
                    logger.info(f"Keyword match: '{kw}' in line: '{line}'")
                    return (tag, 1.0)  # 明确命中关键词，打满分

        # 2. fallback 使用向量匹配
        tag, score = self.vector_classify_line(line)
        if score >= self.threshold:
            logger.info(
                f"Vector match: '{tag}' with score {score:.2f} for line: '{line}'"
            )
            return (tag, score)
        else:
            return (None, score)

    @timeit()
    def detect_headers(self, lines: List[str]):
        logger.debug("开始并行识别 Section Header...")

        tag_heaps: Dict[str, List[Tuple[float, int, str]]] = defaultdict(list)
        with ThreadPoolExecutor(max_workers=8) as execcutor:
            future_to_idx = {
                execcutor.submit(self.is_section_header, line): idx
                for idx, line in enumerate(lines)
            }

            for future in future_to_idx:
                idx = future_to_idx[future]
                try:
                    tag, score = future.result()
                    if tag is not None:
                        heapq.heappush(tag_heaps[tag], (-score, idx))

                except Exception as e:
                    logger.warning(
                        f"[detect_sections] Line {idx} header detection failed: {e}"
                    )

        return tag_heaps

    @timeit()
    def detect_headers_sync(self, lines: List[str]):
        tag_heaps: Dict[str, List[Tuple[float, int, str]]] = defaultdict(list)
        for idx, line in enumerate(lines):
            (tag, score) = self.is_section_header(line)
            if tag is not None:
                heapq.heappush(tag_heaps[tag], (-score, idx))  # 使用负分数实现最大堆
        return tag_heaps

    def detect_sections(self, lines: List[str]) -> Dict[str, List[str]]:
        for idx, line in enumerate(lines):
            logger.debug(f"Processing line {idx}: '{line}'")

        tag_heaps = self.detect_headers(lines)

        # 防止 tag_heaps 为空的情况
        if tag_heaps is None or not tag_heaps:
            return {"personal_info": lines}

        # 获取每个 tag 的最佳行号和分数
        tag_best: Dict[str, Tuple[float, int]] = {}
        for tag, heap in tag_heaps.items():
            score_neg, idx = heapq.heappop(heap)
            tag_best[tag] = (-score_neg, idx)

        # 3. 排序所有 header 行号
        header_list: List[Tuple[int, str]] = sorted(
            [(idx, tag) for tag, (_, idx) in tag_best.items()]
        )

        for tag, (score, idx) in tag_best.items():
            logger.info(f"Best match for '{tag}': line {idx} with score {score:.2f}")

        # 4. 按 header 行号切分内容
        section_map: Dict[str, List[str]] = {}
        for i, (start_idx, tag) in enumerate(header_list):
            # 如果是第一个 header，起始行号为 0
            if i == 0:
                start_idx = 0
            end_idx = header_list[i + 1][0] if i + 1 < len(header_list) else len(lines)
            section_map[tag] = lines[start_idx:end_idx]
            logger.info(f"Detected section '{tag}' from line {start_idx} to {end_idx}")

        return section_map

    def parse_resume(self, ocr_text: str) -> Dict[str, SectionBase]:
        lines = self.normalize_text(ocr_text, keep_blank=True)
        section_lines = self.detect_sections(lines)

        structured_sections = {}
        for section, line_list in section_lines.items():

            raw_text = "\n".join(line_list)

            logger.info(f"Parsing section '{section}' with lines: {line_list}")

            cls = SECTION_BASE.get(section)
            if cls:
                section_obj = cls(section, raw_text)
                section_obj.original_lines = line_list
                section_obj.parse()
                structured_sections[section] = section_obj
            else:
                fallback = SectionBase(section, raw_text)
                fallback.original_lines = line_list
                fallback.parsed_data = {"raw": raw_text}
                structured_sections[section] = fallback

        return structured_sections


if __name__ == "__main__":
    sample_text = """
    
    张三
    电话: 13800001111
    邮箱: zhangsan@example.com
    地址: 北京市海淀区中关村大街27号
    GitHub: github.com/zhangsan
    LinkedIn: linkedin.com/in/zhangsan
    
    
    技能特长
    编程语言：Python, Go, Java, C++
    后端技术：Django, FastAPI, Redis, Kafka, MySQL, MongoDB
    工具与平台：Docker, Kubernetes, Git, Linux
    AI & NLP：Transformers, PaddleOCR, sentence-transformers
    语言能力：英语（CET-6 530），普通话（二甲）

    教育背景
    2015.09 - 2019.06 清华大学 软件工程 本科
    - GPA：3.8/4.0（专业前10%）
    - 主修课程：操作系统、计算机网络、人工智能、软件工程、数据库系统


    项目经历
    2023.01 - 2023.04 智能简历解析平台（个人项目）
    - 技术栈：Python, PaddleOCR, FastAPI, Sentence-BERT
    - 设计一套支持中英文简历识别的端到端平台，准确提取教育、项目、技能等结构化信息
    - 使用嵌入向量和聚类算法，提升 section 匹配准确率至92%

    2022.06 - 2022.08 企业内推系统（校内合作项目）
    - 使用 Django + Vue 实现一套简历内推与岗位推荐平台
    - 集成 Elasticsearch 实现关键词匹配与倒排索引，实现岗位相似度排序

    证书与奖项
    - 2022 年中国软件杯二等奖
    - 国家奖学金（2017-2018学年）
    - 腾讯犀牛鸟精英实习生认证

    工作经历
    2021.07 - 至今  字节跳动（北京）  
    后端研发工程师｜推荐系统平台组
    - 负责用户画像服务模块的优化，提升接口响应速度30%
    - 基于Redis + Flink 实现行为日志的实时聚合服务，服务日均处理10亿条记录
    - 推动服务容器化上线，撰写 CI/CD 脚本并部署至Kubernetes集群

    2020.07 - 2021.06  腾讯实习生  
    实习岗位：后台开发实习生（云服务部门）
    - 参与搭建内部配置平台，支持10+项目的配置热更新
    - 使用Go开发配置管理服务，结合Etcd实现高可用分布式存储
"""

    parser = VectorParser()
    structured = parser.parse_resume(sample_text)

    print(f"共解析出 {len(structured)} 个 section：\n")
    for section, obj in structured.items():
        print(f"Section: {section}")
        print(obj.raw_text)
        print(type(obj))
