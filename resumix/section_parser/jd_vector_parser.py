import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


from typing import Dict, List, Tuple, Union
from resumix.section_parser.jd_section_labels import JDSectionLabels
from resumix.section_parser.base_parser import BaseParser
from resumix.utils.url_fetcher import UrlFetcher
import requests
import chardet
from bs4 import BeautifulSoup
from resumix.utils.llm_client import LLMClient
import json
from resumix.utils.logger import logger
from resumix.section.section_base import SectionBase


class JDVectorParser(BaseParser):
    def __init__(
        self, model_name="paraphrase-multilingual-MiniLM-L12-v2", threshold=0.65
    ):
        section_labels = JDSectionLabels.get_labels(["zh", "en"])
        super().__init__(section_labels, model_name, threshold)
        self.llm_client = LLMClient()

    def parse(self, jd_text: str) -> Dict[str, SectionBase]:
        """
        尝试使用 LLM 提取结构化 JD 段落；若失败则回退到向量匹配。
        返回格式为 Dict[str, SectionBase]，每个字段对应一个段落对象。
        """
        try:
            llm_sections = self.parse_with_llm(jd_text)
            logger.info(f"LLM Sections: {llm_sections}")

            if not isinstance(llm_sections, dict):
                raise ValueError("LLM返回值不是字典类型")

            if not any(llm_sections.values()):
                raise ValueError("LLM返回内容为空")

            structured_sections = {}

            for tag, content in llm_sections.items():
                try:
                    # 合并嵌套结构为纯文本
                    if isinstance(content, dict):
                        lines = [
                            f"{k}: {v}"
                            for k, v in content.items()
                            if isinstance(v, str) and v.strip()
                        ]
                        text = "\n".join(lines)
                    elif isinstance(content, str):
                        text = content.strip()
                    else:
                        raise TypeError(f"段落 {tag} 类型非法：{type(content)}")

                    if not text:
                        raise ValueError(f"段落 {tag} 内容为空")

                    line_list = self.normalize_text(text, keep_blank=True)
                    raw_text = "\n".join(line_list)
                    tag_key = tag.lower().replace(" ", "_")

                    cls = SectionBase
                    section_obj = cls(tag_key, raw_text)
                    section_obj.original_lines = line_list
                    section_obj.parsed_data = {"raw": raw_text}

                    structured_sections[tag_key] = section_obj
                except Exception as e_section:
                    logger.warning(
                        f"[JDVectorParser] 段落处理失败: {tag} - {e_section}"
                    )

            if structured_sections:
                logger.info("[JDVectorParser] Parsed sections with LLM")
                return structured_sections
            else:
                raise ValueError("所有段落处理失败，无有效结构")

        except Exception as e:
            import traceback

            logger.warning(
                f"[JDVectorParser] LLM parsing failed, fallback to vector. Reason: {e}"
            )
            logger.debug(traceback.format_exc())

        # fallback：向量结构解析
        try:
            line_list = self.normalize_text(jd_text, keep_blank=True)
            section_lines = self.detect_sections(line_list)
            structured_sections = {}

            for section, lines in section_lines.items():
                raw_text = "\n".join(lines)
                cls = SectionBase
                section_obj = cls(section, raw_text)
                section_obj.original_lines = lines
                section_obj.parsed_data = {"raw": raw_text}
                section_obj.parse()

                logger.info(f"[JDVectorParser] Fallback section '{section}'")
                structured_sections[section] = section_obj

            logger.info("[JDVectorParser] Parsed sections with vector fallback")
            return structured_sections
        except Exception as e:
            logger.error(f"[JDVectorParser] fallback 向量解析也失败: {e}")
            logger.debug(traceback.format_exc())
            return {"overview": SectionBase("overview", "❌ 无法解析 JD 内容。")}

    def fetch_text_from_url(self, url: str) -> str:
        logger.info(f"[JD Fetcher] 开始抓取 URL: {url}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            logger.info(f"[JD Fetcher] HTTP 状态码: {response.status_code}")

            # 自动检测网页编码
            detected = chardet.detect(response.content)
            encoding = detected["encoding"] or "utf-8"
            logger.info(f"[JD Fetcher] 检测到网页编码: {encoding}")

            html = response.content.decode(encoding, errors="replace")
            soup = BeautifulSoup(html, "html.parser")

            # 清除非正文区域
            for tag in soup(
                [
                    "script",
                    "style",
                    "noscript",
                    "footer",
                    "header",
                    "nav",
                    "form",
                    "meta",
                    "aside",
                ]
            ):
                tag.decompose()

            # 提取正文段落
            tags = soup.find_all(["p", "li", "div", "section"])
            text_lines = [
                t.get_text(strip=True) for t in tags if t.get_text(strip=True)
            ]
            logger.info(f"[JD Fetcher] 抽取文本段落数量: {len(text_lines)}")

            if not text_lines:
                logger.warning(
                    "[JD Fetcher] 抓取结果为空，可能被反爬或内容为 JS 渲染。"
                )

            return "\n".join(text_lines)

        except requests.exceptions.RequestException as e:
            logger.error(f"[JD Fetcher] 请求失败: {e}")
            return ""

        except Exception as e:
            logger.error(f"[JD Fetcher] 抓取解析异常: {e}")
            return ""

    PROMPT = """
You are an expert in structured information extraction. Your task is to extract structured sections from raw webpage content based on the specified labels. Please strictly follow the label definitions provided below.

### Task Objective:
Parse the input job description into a structured format. Each section of the content should correspond to one of the labels. If a particular section is not present in the content, keep the label in the output with an empty string.

### The labels are:
- Overview (Job Title, Location)
- Responsibilities
- Requirements Basic
- Requirements Preferred

### Requirements:
1. The output must be in valid JSON format.
2. Each label should be a top-level field in the JSON, and its value should contain the corresponding content.
3. Try to preserve the original expressions; do not rewrite, summarize, or omit.
4. If the content includes bullet points, keep their original structure.

### Input content (from webpage):
"""

    def parse_with_llm(self, jd_text: str) -> Dict[str, str]:
        prompt = self.PROMPT + jd_text.strip()
        response = self.llm_client(prompt)

        logger.debug(f"[JDVectorParser] Raw LLM response: {repr(response)}")

        def clean_json(text: str) -> str:
            text = text.strip()

            # 去掉开头 ```json 或 ```
            if text.startswith("```"):
                text = re.sub(r"^```(json)?", "", text)
            # 去掉结尾 ```
            if text.endswith("```"):
                text = text[:-3]
            return text.strip()

        try:
            cleaned = clean_json(response)

            if not cleaned:
                raise ValueError("LLM 返回为空或内容无效")

            parsed = json.loads(cleaned)

            if not isinstance(parsed, dict):
                raise TypeError(f"LLM 返回 JSON 类型错误: {type(parsed)}")

            logger.info(f"[JDVectorParser] LLM JSON解析成功，字段数: {len(parsed)}")
            return parsed

        except json.JSONDecodeError as je:
            logger.warning(f"[JDVectorParser] JSONDecodeError: {je}")
        except Exception as e:
            logger.warning(f"[JDVectorParser] LLM parsing failed: {e}")

        # fallback 兜底结构，防止后续代码崩溃
        return {
            "Overview": "",
            "Responsibilities": "",
            "Basic Qualifications": "",
            "Preferred Qualifications": "",
            "RawText": response,
        }


if __name__ == "__main__":
    sample_jd = """
DESCRIPTION
The Healthcare AI organization in AWS is seeking a Software Development Engineer to build new v1 services and contribute to existing services such as HealthLake, Comprehend Medical, and HealthScribe. Our products leverage cloud computing and artificial intelligence to improve healthcare outcomes, reduce costs, and enhance care delivery. You will be part of a diverse team driven by the mission to improve people's lives through innovative technology solutions.

Key job responsibilities
- Design and develop scalable, efficient software systems for healthcare AI services
- Write high-quality, well-tested code for cloud-based healthcare applications
- Collaborate with product managers, applied scientists, and other engineers to implement product features
- Participate in code reviews and technical discussions
- Help maintain operational excellence and compliance with industry standards
- Work on data processing, analytics, and machine learning systems for healthcare applications
- Contribute to technical discussions and help drive continuous improvement

A day in the life
Inclusive Team Culture
Here at Amazon, we embrace our differences. We are committed to furthering our culture of inclusion. We have ten employee-led affinity groups, reaching 40,000 employees in over 190 chapters globally. We have innovative benefit offerings, and host annual and ongoing learning experiences, including our Conversations on Race and Ethnicity (CORE) and AmazeCon (gender diversity) conferences. Amazon’s culture of inclusion is reinforced within our 14 Leadership Principles, which remind team members to seek diverse perspectives, learn and be curious, and earn trust.

Work/Life Balance
Our team puts a high value on work-life balance. It isn’t about how many hours you spend at home or at work; it’s about the flow you establish that brings energy to both parts of your life. We believe striking the right balance between your personal and professional life is critical to life-long happiness and fulfillment. We offer flexibility in working hours and encourage you to find your own balance between your work and personal lives.

Mentorship & Career Growth
Our team is dedicated to supporting new members. We have a broad mix of experience levels and tenures, and we’re building an environment that celebrates knowledge sharing and mentorship. We care about your career growth and strive to assign opportunities based on what will help each team member develop into a better-rounded contributor.

About the team
- Shape the future of AI for healthcare.
- Work on meaningful problems that improve lives globally.
- Access to industry leading technology and vast resources.
- Collaborate with world-class researchers and engineers.

BASIC QUALIFICATIONS
- 3+ years of non-internship professional software development experience
- 2+ years of non-internship design or architecture (design patterns, reliability and scaling) of new and existing systems experience
- Experience programming with at least one software programming language

PREFERRED QUALIFICATIONS
- 3+ years of full software development life cycle, including coding standards, code reviews, source control management, build processes, testing, and operations experience
- Bachelor's degree in computer science or equivalent

Amazon is an equal opportunity employer and does not discriminate on the basis of protected veteran status, disability, or other legally protected status.

Los Angeles County applicants: Job duties for this position include: work safely and cooperatively with other employees, supervisors, and staff; adhere to standards of excellence despite stressful conditions; communicate effectively and respectfully with employees, supervisors, and staff to ensure exceptional customer service; and follow all federal, state, and local laws and Company policies. Criminal history may have a direct, adverse, and negative relationship with some of the material job duties of this position. These include the duties and responsibilities listed above, as well as the abilities to adhere to company policies, exercise sound judgment, effectively manage stress and work safely and respectfully with others, exhibit trustworthiness and professionalism, and safeguard business operations and the Company’s reputation. Pursuant to the Los Angeles County Fair Chance Ordinance, we will consider for employment qualified applicants with arrest and conviction records.

Our inclusive culture empowers Amazonians to deliver the best results for our customers. If you have a disability and need a workplace accommodation or adjustment during the application and hiring process, including support for the interview or onboarding process, please visit https://amazon.jobs/content/en/how-we-hire/accommodations for more information. If the country/region you’re applying in isn’t listed, please contact your Recruiting Partner.

Our compensation reflects the cost of labor across several US geographic markets. The base pay for this position ranges from $129,300/year in our lowest geographic market up to $223,600/year in our highest geographic market. Pay is based on a number of factors including market location and may vary depending on job-related knowledge, skills, and experience. Amazon is a total compensation company. Dependent on the position offered, equity, sign-on payments, and other forms of compensation may be provided as part of a total compensation package, in addition to a full range of medical, financial, and/or other benefits. For more information, please visit https://www.aboutamazon.com/workplace/employee-benefits. This position will remain posted until filled. Applicants should apply via our internal or external career site.
    """
    html = (
        "https://www.amazon.jobs/en/jobs/2886461/devops-engineer-esc-managed-operations"
    )
    parser = JDVectorParser()
    # parser.parse(sample_jd)
    text = UrlFetcher.fetch(html)

    logger.info(text)
    structured = parser.parse(text)

    # structured = parser.parse(sample_jd)

    for k, v in structured.items():
        logger.info(f"{k}:{v}")
