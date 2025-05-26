from .resume_section import ResumeSection
import re
 
class ProjectSection(ResumeSection):
    """项目经历模块：提取每个项目的标题和简要描述"""
    def parse_projects(self) -> list[dict[str, str]]:
        lines = [line.strip() for line in self.raw_text.splitlines() if line.strip()]
        projects = []
        current_project = None

        for line in lines:
            if re.match(r"^\d{4}.*", line):  # 例如：2020 OCR智能识别系统开发
                if current_project:
                    projects.append(current_project)
                current_project = {"title": line, "description": ""}
            elif line.startswith("-") and current_project:
                current_project["description"] += line + "\n"
            elif current_project:
                current_project["description"] += line + "\n"

        if current_project:
            projects.append(current_project)

        # 去除尾部空行并清洗描述
        for p in projects:
            p["description"] = p["description"].strip()

        return projects

    def to_dict(self) -> dict:
        return {
            "section": self.name,
            "projects": self.parse_projects()
        }