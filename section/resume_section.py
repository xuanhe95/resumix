class ResumeSection:
    def __init__(self, name: str, raw_text: str):
        self.name = name
        self.raw_text = raw_text.strip()
        self.lines = [line.strip() for line in self.raw_text.splitlines() if line.strip()]
        self.structured_data = None  # 由子类赋值

    def clean_text(self):
        """可选：对 raw_text 做进一步清洗"""
        return self.raw_text

    def extract_items(self):
        """提取主要内容（默认返回行列表，子类应重写）"""
        return self.lines

    def parse(self):
        """子类应实现：将内容结构化，如解析出时间段、机构名、技能词等"""
        raise NotImplementedError

    def to_dict(self):
        return {
            "section": self.name,
            "content": self.raw_text,
            "parsed": self.structured_data or self.extract_items()
        }

    def to_markdown(self) -> str:
        return f"### {self.name.title()}\n" + "\n".join(self.extract_items())

    def __str__(self):
        return f"== {self.name.upper()} ==\n" + self.raw_text
