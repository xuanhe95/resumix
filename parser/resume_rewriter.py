class ResumeRewriter:
    def __init__(self, llm):
        self.llm = llm

    def rewrite_section(self, section_title: str, section_text: str, jd_text: str) -> str:
        prompt = f"""
            你是一个专业的简历优化助手，请根据以下岗位描述，对简历中的 [{section_title}] 部分进行改写，使其内容更贴合岗位需求。

            岗位描述：
            {jd_text}

            原始简历内容：
            \"\"\"{section_text}\"\"\"
            请以精炼、有力、岗位契合度高的风格输出改写后的内容。
            """
        return self.llm(prompt)

    def rewrite_resume(self, sections: dict, jd_text: str) -> dict:
        rewritten = {}
        for section_title, section_text in sections.items():
            rewritten[section_title] = self.rewrite_section(section_title, section_text, jd_text)
        return rewritten
