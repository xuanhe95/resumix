import os
import fitz  # PyMuPDF
import tempfile
from paddleocr import PaddleOCR
import requests
import streamlit as st

# Initialize PaddleOCR (supporting Chinese + angle recognition)
ocr_model = PaddleOCR(use_angle_cls=True, lang="ch")

model_name = "llama3.2:3b"


def call_local_llm(prompt, model=model_name):
    try:
        res = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        return res.json().get("response", "⚠️ Model did not return a result.")
    except Exception as e:
        return f"❌ Error calling local model: {e}"


def extract_text_from_pdf(pdf_file):
    # Use tempfile to save the uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(pdf_file.read())  # Write the content of the uploaded file
        temp_file_path = temp_file.name  # Get the temporary file path

    # Open the temporary file using PyMuPDF (fitz)
    doc = fitz.open(temp_file_path)
    full_text = ""
    for i in range(1):
        page = doc.load_page(i)
        pix = page.get_pixmap(dpi=150)
        img_path = f"temp_page_{i}.png"
        pix.save(img_path)

        ocr_result = ocr_model.ocr(img_path, cls=True)
        page_text = "\n".join([line[1][0] for block in ocr_result for line in block])
        full_text += f"\n--- Page {i + 1} ---\n{page_text}"
        os.remove(img_path)

    # Clean up temporary PDF file
    os.remove(temp_file_path)

    return full_text.strip()


# Streamlit UI
st.title("📄 Local PDF Reader AI Agent")
st.markdown("Upload PDF → OCR → Local LLM Processing")

uploaded_file = st.file_uploader("Upload PDF file", type="pdf")
task = st.radio("Choose task", ["Summarize", "Question"], index=0)

if uploaded_file is not None:
    st.write("File uploaded, processing...")
    text = extract_text_from_pdf(uploaded_file)
    if text:
        prompt = (
            f"Summarize the following:\n{text}"
            if task == "Summarize"
            else f"{text}\n\nAnswer the following questions based on the content:"
        )
        result = call_local_llm(prompt)
        st.text_area("AI Output", result, height=200)
    else:
        st.write("⚠️ No text found in the PDF.")
