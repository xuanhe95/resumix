class SectionBase:
    def __init__(self, name:str, raw_text:str):
        self.name 
        self.raw_text = raw_text
    

    def parse(self):
        raise NotImplementedError
    
    