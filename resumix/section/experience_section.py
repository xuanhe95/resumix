from resumix.section.section_base import SectionBase


class ExperienceSection(SectionBase):
    def parse(self):
        entries = []
        chunks = self.raw_text.split("\n\n")
        for chunk in chunks:
            lines = chunk.strip().splitlines()
            if len(lines) >= 2:
                company = lines[0]
                title_and_date = lines[1]
                highlights = [l for l in lines[2:] if l.startswith("-")]
                entries.append(
                    {
                        "company": company,
                        "position": title_and_date,
                        "startDate": "",
                        "endDate": "",
                        "location": "",
                        "highlights": [h.lstrip("- ").strip() for h in highlights],
                    }
                )
        self.parsed_data = entries
