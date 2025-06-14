import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


from typing import Dict, List
from jd_section_labels import JDSectionLabels
from section_parser.base_parser import BaseParser
import requests
import chardet
from bs4 import BeautifulSoup
from utils.llm_client import LLMClient
import json


class JDVectorParser(BaseParser):
    def __init__(
        self, model_name="paraphrase-multilingual-MiniLM-L12-v2", threshold=0.65
    ):
        section_labels = JDSectionLabels.get_labels(["zh", "en"])
        super().__init__(section_labels, model_name, threshold)
        self.llm_client = LLMClient(
            base_url="http://localhost:11434/api/generate", model_name="llama3.2:3b"
        )

    def parse(self, jd_text: str) -> Dict[str, List[str]]:
        lines = self.normalize_text(jd_text, keep_blank=True)
        section_map = self.detect_sections(lines)
        return section_map

    def fetch_text_from_url(self, url: str) -> str:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # 自动检测编码（更强健）
        detected = chardet.detect(response.content)
        encoding = detected["encoding"] or "utf-8"
        html = response.content.decode(encoding, errors="replace")

        soup = BeautifulSoup(html, "html.parser")

        # 过滤掉 script/style 等无用标签
        for tag in soup(
            ["script", "style", "noscript", "footer", "header", "nav", "form", "meta"]
        ):
            tag.decompose()

        tags = soup.find_all(["p", "li", "div", "section"])
        text = "\n".join(t.get_text(strip=True) for t in tags if t.get_text(strip=True))
        return text

    PROMPT = """
    你将作为结构化信息提取专家，输入为网页正文内容，输出为结构化段落。请严格按照我提供的标签（labels）进行分段提取。

        ### 任务目标：
        将网页正文内容解析成指定结构，每一段对应一个标签（label）。若某个标签在网页中无对应内容，则保留标签但内容为空字符串。

        ### 我的标签如下：
        - Overview (Job Title, Location)
        - Responsibilities
        - Basic Qualifications
        - Preferred Qualifications

        ### 要求：
        1. 使用 JSON 格式输出；
        2. 每个标签作为一个字段，字段值为该部分正文内容；
        3. 尽量保持原始表达，不要改写、总结或省略；
        4. 若有 bullet points，请保留其结构。

        ### 输入正文（网页内容）如下：
        """

    def parse_with_llm(self, jd_text: str) -> str:
        prompt = self.PROMPT + jd_text.strip()
        response = self.llm_client(prompt)
        try:
            structured_data = json.loads(response)
            return json.dumps(structured_data, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
            return response  # 如果解析失败也返回原始文本


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
    html = "https://www.amazon.jobs/en/jobs/2975712/software-dev-engineer-ii-aws-healthcare-ai"
    parser = JDVectorParser()

    # text = parser.fetch_text_from_url(html)
    # structured = parser.parse_with_llm(text)

    structured = parser.parse(sample_jd)

    print(f"共解析出 {len(structured)} 个 JD 段落：\n")
    for section, lines in structured.items():
        print(f"Section: {section}")
        print("---" * 20)
        print("\n".join(lines))
        print("\n---\n")
