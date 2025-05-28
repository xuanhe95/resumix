import fitz  # PyMuPDF
import tempfile
import os


class OCRUtils:
    def __init__(self, ocr_model, dpi: int = 150, keep_images: bool = False):
        """
        初始化 OCR 提取器。

        参数：
            ocr_model: 初始化后的 PaddleOCR 实例。
            dpi: 渲染 PDF 图像的分辨率。
            keep_images: 是否保留中间图像文件（调试用）。
        """
        self.ocr_model = ocr_model
        self.dpi = dpi
        self.keep_images = keep_images

    def extract_text(self, pdf_file, max_pages: int = 1) -> str:
        """
        从上传的 PDF 文件中提取 OCR 文本。

        参数：
            pdf_file: Streamlit 上传的 FileUploader 对象或 file-like 对象。
            max_pages: 最多提取多少页（从第一页开始）。

        返回：
            提取的纯文本内容。
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:

            content = pdf_file.read()
            if not content:
                raise ValueError("上传的 PDF 文件内容为空。")

            temp_file.write(content)
            temp_pdf_path = temp_file.name

        doc = fitz.open(temp_pdf_path)
        full_text = ""

        for i in range(min(len(doc), max_pages)):
            page = doc.load_page(i)
            pix = page.get_pixmap(dpi=self.dpi)
            img_path = f"temp_page_{i}.png"
            pix.save(img_path)

            ocr_result = self.ocr_model.ocr(img_path, cls=True)
            page_text = "\n".join(
                [line[1][0] for block in ocr_result for line in block]
            )
            full_text += f"\n--- Page {i + 1} ---\n{page_text}"

            if not self.keep_images:
                os.remove(img_path)

        os.remove(temp_pdf_path)
        return full_text.strip()
