import requests
import chardet
from bs4 import BeautifulSoup
import sys
import os


class JDParser:
    def __init__(self, llm):
        self.llm = llm

    def fetch_text_from_url(self, url: str) -> str:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # 自动检测编码（更强健）
        detected = chardet.detect(response.content)
        encoding = detected["encoding"] or "utf-8"
        html = response.content.decode(encoding, errors="replace")

        soup = BeautifulSoup(html, "html.parser")
        tags = soup.find_all(["p", "li", "div", "section"])
        text = "\n".join(t.get_text(strip=True) for t in tags if t.get_text(strip=True))
        return text

    def parse_jd(self, jd_text: str) -> str:
        prompt = f"""
        请从下面的岗位描述中提取结构化信息：

        岗位描述：
            \"\"\"{jd_text}\"\"\"

            请输出：
            - 岗位名称：
            - 所属部门：
            - 岗位职责（分点）：
            - 任职要求（分点）：
            - 所需技能（技能列表）：
        """
        return self.llm(prompt)

    def parse_from_url(self, url: str) -> str:
        jd_text = self.fetch_text_from_url(url)
        return self.parse_jd(jd_text)


if __name__ == "__main__":
    # 示例：使用本地 LLM 客户端
    from utils.llm_client import LLMClient

    llm = LLMClient()
    parser = JDParser(llm)

    # 示例 URL
    url = "https://cs.bit.edu.cn/zsjy/jyysxxx/133bda5a688f415ab96740027d974793.htm"
    structured_jd = parser.parse_from_url(url)
    print(structured_jd)
