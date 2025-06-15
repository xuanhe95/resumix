from keybert import KeyBERT
from typing import List, Tuple
import re
import threading
from sentence_transformers import util, SentenceTransformer


class KeywordExtractor:
    _instance = None
    _lock = threading.Lock()  # 保证线程安全

    def __new__(cls, model_name: str = "all-MiniLM-L6-v2"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init_model(model_name)
        return cls._instance

    def _init_model(self, model_name: str):
        """
        初始化 KeyBERT 模型。只会在首次创建实例时执行。
        """
        self.model = KeyBERT(model_name)
        self.embedder = SentenceTransformer(model_name)

    def extract_keywords(
        self,
        text: str,
        candidates: List[str] = [],
        top_k: int = 10,
        dict_only: bool = False,
        custom_dict: List[str] = None,
    ) -> List[str]:
        """
        提取关键词。
        :param text: 输入文本。
        :param top_k: 返回前 top_k 个关键词。
        :param dict_only: 是否只返回技术关键词。
        :param custom_dict: 自定义技术词汇表（用于过滤）。
        :return: List[str] 提取的关键词。
        """

        if candidates:
            candidates = [c.lower() for c in candidates]

        keywords = self.model.extract_keywords(
            text.lower(),
            candidates=candidates,
            top_n=top_k,
            use_mmr=True,
            diversity=0.5,
            stop_words="english",
        )
        keyword_list = [(kw, score) for kw, score in keywords]

        if dict_only and custom_dict:
            custom_set = set(kw.lower() for kw in custom_dict)
            keyword_list = [
                (kw, score) for (kw, score) in keyword_list if kw.lower() in custom_set
            ]

        return keyword_list

    def extract_relevant_keywords(
        self,
        jd_text: str,
        resume_text: str,
        top_k: int = 10,
        dict_only: bool = False,
        custom_dict: List[str] = None,
    ) -> List[Tuple[str, float]]:
        """
        从 JD 中提取与简历语义最相关的句子的关键词。
        """

        jd_sentences = [s.strip() for s in jd_text.split("\n") if s.strip()]
        resume_embedding = self.embedder.encode(resume_text, convert_to_tensor=True)
        jd_embeddings = self.embedder.encode(jd_sentences, convert_to_tensor=True)

        cosine_scores = util.cos_sim(resume_embedding, jd_embeddings)[0]

        k = min(top_k, len(jd_sentences))
        top_indices = cosine_scores.topk(k).indices.tolist()

        selected_text = " ".join([jd_sentences[i] for i in top_indices])

        # 提取关键词
        candidates = None
        if dict_only and custom_dict:
            candidates = [kw.lower() for kw in custom_dict]

        return self.extract_keywords(
            selected_text,
            top_k=top_k,
            candidates=candidates,
            dict_only=dict_only,
            custom_dict=custom_dict,
        )


# ✅ 使用示例
if __name__ == "__main__":
    text = """
Overview
Do you want to be a part of a multi-billion-dollar organization that is rapidly growing and is responsible for 200M MAU and exabytes of customer data in the cloud at high performance and scale? Do you want to work on technically challenging problems on the cloud in a full-stack environment, with an opportunity to influence the roadmap and vision of not only your team but your partner teams as well? If so, come join the OneDrive-SharePoint (ODSP) team as part of Office M365 ecosystem in Noida!  

 

SharePoint helps millions of people work better together and empowers the biggest companies in the world to solve mission critical problems. We create global scale services to store, secure and manage some of the most sensitive data on the planet. We have fantastic opportunities and are on the front-line of making many of our next generation architecture investments to deliver world-class service management, autonomous cloud & regulated clouds, deployments & engineering systems capabilities using cutting-edge technology.  

 

Microsoft is uniquely at the center of this opportunity, and we have the responsibility to advance the frontiers of compliance, regulation and security in the ever expanding digital world. We are looking for a Strong Senior Backend Engineer to take this mission forward. 

 

Microsoft’s mission is to empower every person and every organization on the planet to achieve more. As employees we come together with a growth mindset, innovate to empower others, and collaborate to realize our shared goals. Each day we build on our values of respect, integrity, and accountability to create a culture of inclusion where everyone can thrive at work and beyond.

Qualifications
Required Qualifications:

Bachelor's Degree in Computer Science or related technical field AND 5+ years technical engineering experience with coding in languages including, but not limited to, C, C++, C#, Java, JavaScript, or Python
OR equivalent experience.
Other Requirements:

 

Ability to meet Microsoft, customer and/or government security screening requirements are required for this role. These requirements include but are not limited to the following specialized security screenings:

Microsoft Cloud Background Check: This position will be required to pass the Microsoft Cloud background check upon hire/transfer and every two years thereafter.
Preferred Qualifications:

Bachelor's Degree in Computer Science or related technical field AND 5+ years technical engineering experience with coding in languages including, but not limited to, C, C++, C#, Java, JavaScript, or Python
OR Master's Degree in Computer Science or related technical field AND 6+ years technical engineering experience with coding in languages including, but not limited to, C, C++, C#, Java, JavaScript, or Python
OR equivalent experience.
Working in agile teams with strong customer focus. 
Good communication and cross group collaboration skills .
Experience in Azure, Exchange, or other cloud and distributed systems.
Proven track record of mentoring, and growing junior engineers.
Demonstrated independence, bias for action, and tolerance for ambiguity.

 

#SharePointIndia  

 


Responsibilities
Towards this vision, we are seeking a Sr Engineer to disrupt and build next generation of products and take it to the next level. Your responsibilities will include: 

Own and influence the architecture roadmap and vision along with strong execution. 
Influence the product vision by working closely with product development and engineering teams and ensure best quality design and architecture. 
Lead key technical initiatives and serve as the lead on our most technically complex, cross-functional projects. 
Design systems for scalability and performance with highest quality and following best engineering practices. 
Lead the design, get hands dirty and write/review code/design and finally deploy the best code into production 
Assist in the career development of others, actively mentoring individuals and the community on advanced technical issues. 
Create and execute appropriate quality plans, test strategies and processes 
You must be self-driven, curious to learn, proactive, and result-oriented.  
    """
    tech_words = [
        "python",
        "fastapi",
        "mongodb",
        "docker",
        "kubernetes",
        "tensorflow",
        "aws",
        "azure",
        "ci/cd",
        "pytorch",
        "react",
        "vue",
        "hadoop",
    ]

    extractor = KeywordExtractor()
    all_keywords = extractor.extract_keywords(text, top_k=50)
    tech_keywords = extractor.extract_keywords(
        text, dict_only=True, custom_dict=tech_words
    )

    print("All Keywords:", all_keywords)
    print("Technical Keywords:", tech_keywords)
