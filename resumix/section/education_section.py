import re
from section.section_base import SectionBase


class EducationSection(SectionBase):
    def parse(self):
        lines = self.raw_text.splitlines()
        self.parsed_data = []

        for line in lines:
            match = re.match(
                r"(\\d{4})[-–](\\d{4})\\s+(\\S+)\\s+(\\S+)\\s+(\\S+)", line
            )
            if match:
                start, end, school, major, degree = match.groups()
                self.parsed_data.append(
                    {
                        "institution": school,
                        "area": major,
                        "studyType": degree,
                        "startDate": start,
                        "endDate": end,
                        "additionalAreas": [],
                        "score": "",
                        "location": "",
                    }
                )
