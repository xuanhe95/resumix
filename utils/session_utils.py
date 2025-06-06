from utils.ocr_utils import OCRUtils
import streamlit as st
from parser.jd_parser import JDParser
from paddleocr import PaddleOCR


@st.cache_data(show_spinner="正在提取简历文本...")
def extract_text_from_pdf(file):
    ocr_model = PaddleOCR(use_angle_cls=True, lang="ch")
    ocr = OCRUtils(ocr_model, dpi=150, keep_images=False)
    return ocr.extract_text(file, max_pages=1)


@st.cache_data(show_spinner="正在解析岗位描述...")
def extract_job_description(jd_url, _llm_model):
    jd_parser = JDParser(_llm_model)
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
        if "jd_content" not in st.session_state:
            if "jd_url" not in st.session_state:
                return "No job description URL provided."
            else:
                st.session_state.jd_content = extract_job_description(
                    st.session_state.jd_url, st.session_state.llm_model
                )
        return st.session_state.jd_content
