from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

resume_content = [
    ("Name:", "Alex Johnson"),
    ("Email:", "alex.johnson@email.com"),
    ("Phone:", "+1 555-123-4567"),
    ("LinkedIn:", "linkedin.com/in/alexjohnson"),
    ("Education:", "B.Sc. in Computer Science, University of Example, 2024"),
    ("GPA:", "3.8/4.0"),
    ("Skills:", "Python, Java, C++, SQL, Machine Learning, Data Structures, Algorithms, Git"),
    ("Projects:", "Smart Resume Parser (NLP, Python)\nPersonal Portfolio Website (React, AWS)"),
    ("Experience:", "Software Engineering Intern, TechCorp, Summer 2023\n- Developed REST APIs in Python\n- Improved CI/CD pipeline"),
    ("Awards:", "Dean's List (2021-2024), ACM ICPC Regional Participant"),
]

def generate_resume_pdf(filename="test.pdf"):
    c = canvas.Canvas(filename, pagesize=LETTER)
    width, height = LETTER
    y = height - 50
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, y, "Alex Johnson")
    y -= 30
    c.setFont("Helvetica", 12)
    c.drawString(50, y, "Email: alex.johnson@email.com    |    Phone: +1 555-123-4567    |    LinkedIn: linkedin.com/in/alexjohnson")
    y -= 40
    for section, content in resume_content[4:]:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, section)
        y -= 20
        c.setFont("Helvetica", 12)
        for line in content.split("\n"):
            c.drawString(70, y, line)
            y -= 18
        y -= 10
    c.save()

if __name__ == "__main__":
    generate_resume_pdf() 