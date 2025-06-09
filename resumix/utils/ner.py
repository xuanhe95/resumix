from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

class ResumeNER:
    def __init__(self, model_name="dslim/bert-base-NER"):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(model_name)
        self.pipeline = pipeline(
            "ner", model=self.model, tokenizer=self.tokenizer, aggregation_strategy="simple"
        )

    def extract_entities(self, text: str) -> dict:
        results = self.pipeline(text)
        entities = {}
        for item in results:
            label = item["entity_group"]
            word = item["word"]
            entities.setdefault(label, []).append(word)
        return entities

# 用法示例
if __name__ == "__main__":
    ner = ResumeNER()
    resume_text = """
    John Smith is a software engineer at Google. He graduated from Stanford University in 2018.
    He is proficient in Python, Docker, and AWS, and worked on AI research in the healthcare domain.
    """
    entities = ner.extract_entities(resume_text)
    for label, items in entities.items():
        print(f"{label}: {items}")
