import re
from section.section_base import SectionBase


class ProjectsSection(SectionBase):
    def parse(self):
        entries = []
        lines = self.raw_text.splitlines()
        name, desc = "", ""
        for line in lines:
            if any(char.isdigit() for char in line):
                if name:
                    entries.append(
                        {
                            "name": name,
                            "description": desc.strip(),
                            "keywords": [],
                            "url": "",
                        }
                    )
                name = line.strip()
                desc = ""
            else:
                desc += line.strip() + " "
        if name:
            entries.append(
                {
                    "name": name,
                    "description": desc.strip(),
                    "keywords": [],
                    "url": "",
                }
            )
        self.parsed_data = entries
