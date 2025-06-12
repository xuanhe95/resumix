from utils.ocr_utils import OCRUtils
import streamlit as st
from parser.jd_parser import JDParser
from paddleocr import PaddleOCR
from resumix.parser.resume_parser import ResumeParser
from resumix.section_parser.vector_parser import VectorParser
from resumix.section_parser.jd_vector_parser import JDVectorParser
from resumix.utils.llm_client import LLMClient
from resumix.utils.logger import logger
from resumix.utils.url_fetcher import UrlFetcher
import easyocr


from config.config import Config

CONFIG = Config().config


@st.cache_data(show_spinner="正在提取简历文本...")
def extract_text_from_pdf(file):
    logger.info("Extracting text from PDF file...")

    ocr_model = None

    if CONFIG.OCR.USE_MODEL == "easyocr":
        ocr_model = easyocr.Reader(
            ["ch_sim", "en"],
            gpu=CONFIG.OCR.EASYOCR.GPU,
            model_storage_directory=CONFIG.OCR.EASYOCR.DIRECTORY,
        )
    elif CONFIG.OCR.USE_MODEL == "paddleocr":
        ocr_model = PaddleOCR(use_angle_cls=True, lang="ch")

    ocr = OCRUtils(ocr_model, dpi=150, keep_images=False)

    return ocr.extract_text(file, max_pages=1)


def extract_job_description(jd_url):
    jd_parser = JDParser(LLMClient())
    jd_content = jd_parser.parse_from_url(jd_url)
    st.chat_message("Job Description").write(jd_content)
    return jd_content


class SessionUtils:
    @staticmethod
    def get_resume_text():
        if "resume_text" not in st.session_state:
            if "uploaded_file" not in st.session_state:
                raise ValueError("No resume file uploaded.")
            else:
                st.session_state.resume_text = extract_text_from_pdf(
                    st.session_state.uploaded_file
                )
        return st.session_state.resume_text

    @staticmethod
    def upload_resume_file(file):
        st.session_state.uploaded_file = file

    @staticmethod
    def get_job_description_content():
        url = st.session_state.get("jd_url", "")
        cached_url = st.session_state.get("jd_cached_url", "")

        # 如果 URL 不存在或没有变化，不重新解析
        if "jd_content" not in st.session_state or url != cached_url:
            if not url:
                logger.info("No JD provided.")
                return "No job description URL provided."
            logger.info(f"Update JD URL to {url}")
            st.session_state.jd_content = extract_job_description(url)
            st.session_state.jd_cached_url = url  # 更新缓存 URL

        return st.session_state.jd_content

    @staticmethod
    def get_resume_sections():
        if "resume_sections" not in st.session_state:
            text = SessionUtils.get_resume_text()
            parser = VectorParser()
            st.session_state.resume_sections = parser.parse_resume(text)
        return st.session_state.resume_sections

    # @staticmethod
    # def get_jd_sections():
    #     if "jd_sections" not in st.session_state:
    #         url = st.session_state.get("jd_url", "").strip()
    #         logger.info(f"URL: {url}")

    #         if not url:
    #             logger.warning("[SessionUtils] URL 未设置，跳过 JD 解析")
    #             return {"overview": ["⚠️ 未提供岗位描述链接"]}

    #         try:
    #             parser = JDVectorParser()

    #             text = UrlFetcher.fetch(url)
    #             logger.info(f"jd text: {text}")

    #             st.session_state.jd_sections = parser.parse(text)
    #         except Exception as e:
    #             logger.error(f"[SessionUtils] 解析 JD 失败: {e}")
    #             st.session_state.jd_sections = {
    #                 "overview": [f"❌ 无法解析 JD 内容：{e}"]
    #             }
    #     else:
    #         logger.info("Loadiing JD Sections...")

    #     return st.session_state.jd_sections

    @staticmethod
    def get_jd_sections():
        url = st.session_state.get("jd_url", "").strip()
        cached_url = st.session_state.get("jd_cached_url", "").strip()

        if not url:
            logger.warning("[SessionUtils] JD URL 未设置，跳过更新")
            st.session_state.jd_sections = {"overview": ["⚠️ 未提供岗位描述链接"]}
            st.session_state.jd_content = "⚠️ 未提供岗位描述链接"
            return st.session_state.jd_sections

        if (
            url == cached_url
            and "jd_sections" in st.session_state
            and "jd_content" in st.session_state
        ):
            logger.info("[SessionUtils] JD URL 未变化，使用缓存内容")
            return st.session_state.jd_sections
        try:
            logger.info(f"[SessionUtils] Fetching and parsing JD from: {url}")
            jd_text = UrlFetcher.fetch(url)
            st.session_state.jd_content = jd_text

            parser = JDVectorParser()
            st.session_state.jd_sections = parser.parse(jd_text)

            st.session_state.jd_cached_url = url  # 缓存 URL

            return st.session_state.jd_sections

        except Exception as e:
            logger.error(f"[SessionUtils] JD 更新失败: {e}")
            st.session_state.jd_sections = {"overview": [f"❌ 无法解析 JD 内容：{e}"]}
            st.session_state.jd_content = f"❌ 无法获取 JD 网页内容：{e}"
            return st.session_state.jd_sections

    @staticmethod
    def get_section_raw(section_name: str) -> str:
        sections = SessionUtils.get_resume_sections()
        return sections.get(section_name).raw_text if section_name in sections else ""

    @staticmethod
    def get_section_data(section_name: str) -> dict:
        sections = SessionUtils.get_resume_sections()
        return sections.get(section_name).to_dict() if section_name in sections else {}
