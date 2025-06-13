from resumix.rewriter.keyword_extractor import KeywordExtractor
from resumix.utils.keywords_loader import KeywordsLoader
from resumix.section_parser.jd_vector_parser import JDVectorParser
from resumix.section_parser.vector_parser import VectorParser
from resumix.modules.score_module.score_module import ScoreModule

if __name__ == "__main__":

    raw_text = """Responsibilities
About Global Payment
The Global Payment team of Bytedance provides payment solutions - including payment acquisitions, disbursements, transaction monitoring, payment method management, foreign exchange conversion, accounting, reconciliations, and so on to ensure that our users have a smooth and secure payment experience on ByteDance platforms including TikTok.

We are looking for talented individuals to join us for an internship in from May 2025 onwards. Internships at ByteDance aim to offer students industry exposure and hands-on experience. Watch your ambitions become reality as your inspiration brings infinite opportunities at ByteDance.

Successful candidates must be able to commit to the following Internships
- From May onwards to August 2025 (full time)
- From August to October 2025 (part time)

Candidates can apply to a maximum of two positions and will be considered for jobs in the order you apply. The application limit is applicable to ByteDance and its affiliates' jobs globally. Applications will be reviewed on a rolling basis - we encourage you to apply early.

Responsibilities
- Build advanced and standardized R&D tools and platforms to accelerate R&D efficiency as well as quality.
- Build and deliver the datacenter to support the expanding business globally.
- Take the shift to respond to the datacenter production issues that impact business, and design the solution to improve the defects as well enhance the capabilities of issue detections.
- Collaborate with product design, product management and other software engineering teams to deliver business values to the users.
Qualifications
Minimum Qualifications:
- Currently pursuing a Bachelor or Master degree in Computer Science, Computer Engineering, or a related technical discipline;
- Proficiency in one or more programming languages (such as Java/Golang/Python, etc.);
- Familiar with backend technologies, including database, concurrency, microservice RPC framework and common network protocols, such as HTTP.
- Familiar with common open source distributed middleware and common components such as MySQL, Redis, RMQ etc.
- Good collaborator and team player, comfortable working in a fast moving, culturally diverse and globally distributed team environment.
- Experience in full-stack tool development is preferred;
- Have public cloud PaaS product experience or similar background knowledge is a plus;
- Experience in the implementation of complex business system architecture is preferred.

Preferred Qualifications:
- Relevant internship experience with hands on exposure to the tech stack
- Interested in payment industry
- Graduating December 2025 onwards with the intent to return to degree program after the completion of the internship.

ByteDance is committed to creating an inclusive space where employees are valued for their skills, experiences, and unique perspectives. Our platform connects people from across the globe and so does our workplace. At ByteDance, our mission is to inspire creativity and enrich life. To achieve that goal, we are committed to celebrating our diverse voices and to creating an environment that reflects the many communities we reach. We are passionate about this and hope you are too.

By submitting an application for this role, you accept and agree to our global applicant privacy policy, which may be accessed here: https://jobs.bytedance.com/en/legal/privacy.

If you have any questions, please reach out to us at apac-earlycareers@bytedance.com
Job Information
About Us
Founded in 2012, ByteDance's mission is to inspire creativity and enrich life. With a suite of more than a dozen products, including TikTok, Lemon8, CapCut and Pico as well as platforms specific to the China market, including Toutiao, Douyin, and Xigua, ByteDance has made it easier and more fun for people to connect with, consume, and create content.​

Why Join ByteDance
Inspiring creativity is at the core of ByteDance's mission. Our innovative products are built to help people authentically express themselves, discover and connect – and our global, diverse teams make that possible. Together, we create value for our communities, inspire creativity and enrich life - a mission we work towards every day.​

As ByteDancers, we strive to do great things with great people. We lead with curiosity, humility, and a desire to make impact in a rapidly growing tech company. By constantly iterating and fostering an "Always Day 1" mindset, we achieve meaningful breakthroughs for ourselves, our Company, and our users. When we create and grow together, the possibilities are limitless. Join us.​

Diversity & Inclusion​

ByteDance is committed to creating an inclusive space where employees are valued for their skills, experiences, and unique perspectives. Our platform connects people from across the globe and so does our workplace. At ByteDance, our mission is to inspire creativity and enrich life. To achieve that goal, we are committed to celebrating our diverse voices and to creating an environment that reflects the many communities we reach. We are passionate about this and hope you are too."""

    html = "https://jobs.bytedance.com/en/position/7475612286737467656/detail"
    parser = JDVectorParser()

    text = parser.fetch_text_from_url(html)
    # jd_structured = parser.parse_with_llm(text)

    jd_structured = parser.parse(raw_text)

    keyword_extractor = KeywordExtractor()

    tech_keywords = KeywordsLoader.load_keywords(
        "resumix/section_parser/tech_keywords.json"
    )

    sample_text = """
    
    张三
    电话: 13800001111
    邮箱: zhangsan@example.com
    地址: 北京市海淀区中关村大街27号
    GitHub: github.com/zhangsan
    LinkedIn: linkedin.com/in/zhangsan
    
    
    技能特长
    编程语言：Python, Go, Java, C++
    后端技术：Django, FastAPI, Redis, Kafka, MySQL, MongoDB
    工具与平台：Docker, Kubernetes, Git, Linux
    AI & NLP：Transformers, PaddleOCR, sentence-transformers
    语言能力：英语（CET-6 530），普通话（二甲）

    教育背景
    2015.09 - 2019.06 清华大学 软件工程 本科
    - GPA：3.8/4.0（专业前10%）
    - 主修课程：操作系统、计算机网络、人工智能、软件工程、数据库系统


    项目经历
    2023.01 - 2023.04 智能简历解析平台（个人项目）
    - 技术栈：Python, PaddleOCR, FastAPI, Sentence-BERT
    - 设计一套支持中英文简历识别的端到端平台，准确提取教育、项目、技能等结构化信息
    - 使用嵌入向量和聚类算法，提升 section 匹配准确率至92%

    2022.06 - 2022.08 企业内推系统（校内合作项目）
    - 使用 Django + Vue 实现一套简历内推与岗位推荐平台
    - 集成 Elasticsearch 实现关键词匹配与倒排索引，实现岗位相似度排序

    证书与奖项
    - 2022 年中国软件杯二等奖
    - 国家奖学金（2017-2018学年）
    - 腾讯犀牛鸟精英实习生认证

    工作经历
    2021.07 - 至今  字节跳动（北京）  
    后端研发工程师｜推荐系统平台组
    - 负责用户画像服务模块的优化，提升接口响应速度30%
    - 基于Redis + Flink 实现行为日志的实时聚合服务，服务日均处理10亿条记录
    - 推动服务容器化上线，撰写 CI/CD 脚本并部署至Kubernetes集群

    2020.07 - 2021.06  腾讯实习生  
    实习岗位：后台开发实习生（云服务部门）
    - 参与搭建内部配置平台，支持10+项目的配置热更新
    - 使用Go开发配置管理服务，结合Etcd实现高可用分布式存储
"""

    parser = VectorParser()
    section_structured = parser.parse_resume(sample_text)

    resume_text_all = []

    print("=== 解析结果 ===\n")

    print(f"共解析出 {len(section_structured)} 个 section：\n")
    for section, obj in section_structured.items():
        print(f"Section: {section}")
        print(obj.raw_text)
        print(type(obj))
        resume_text_all.append(obj.raw_text)

    resume_full_text = "\n".join(resume_text_all)

    import re

    resume_full_text = "\n".join(resume_text_all)

    # 提取所有的单词，转换为小写并去重
    words = re.findall(r"\b\w+\b", resume_full_text.lower())
    tokens = list(set(words))

    print(f"共解析出 {len(jd_structured)} 个 JD 段落：\n")
    for section, lines in jd_structured.items():
        print(f"Section: {section}")
        print("---" * 20)
        print("\n".join(lines))
        print("\n---\n")

    for section, structure in jd_structured.items():
        print(f"Processing section: {section}")
        keywords = keyword_extractor.extract_relevant_keywords(
            " ".join(structure),
            # candidates=tech_keywords,
            top_k=30,
            resume_text=resume_full_text,
        )
        print(f"提取的关键词：{keywords}")

    score_module = ScoreModule()

    resume_section = section_structured["project"]
