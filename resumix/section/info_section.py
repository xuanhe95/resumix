import re
from resumix.section.section_base import SectionBase


class PersonalInfoSection(SectionBase):
    def parse(self):
        name = ""
        phone = ""
        email = ""

        lines = self.raw_text.splitlines()
        for line in lines:
            if re.search(r"@\w+", line):
                email = line.strip()
            elif re.search(r"\d{3,}", line):
                phone = line.strip()
            elif not name:
                name = line.strip()

        self.parsed_data = {
            "name": name,
            "email": email,
            "phone": phone,
            "website": "",
            "address": "",
        }
