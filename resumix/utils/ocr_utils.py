import os
import time
import tempfile
import fitz  # PyMuPDF
from utils.logger import logger


class OCRUtils:
    def __init__(self, ocr_model=None, dpi: int = 151, keep_images: bool = False):
        """
        通用 OCR 提取器，可自动识别并使用 PaddleOCR 或 EasyOCR。

        参数：
            ocr_model: 已初始化的 OCR 模型（PaddleOCR 或 EasyOCR 的 reader）。
            dpi: 渲染 PDF 图像的分辨率。
            keep_images: 是否保留中间图像文件（调试用）。
        """
        self.ocr_model = ocr_model
        self.dpi = dpi
        self.keep_images = keep_images
        self.backend = self._detect_backend()

    def _detect_backend(self):
        if self.ocr_model is None:
            raise ValueError("OCR model cannot be None.")
        if hasattr(self.ocr_model, "ocr"):
            return "paddle"
        elif hasattr(self.ocr_model, "readtext"):
            return "easyocr"
        else:
            raise TypeError("Unsupported OCR model type.")

    def extract_text(self, pdf_file, max_pages: int = 2) -> str:
        start_time = time.time()
        logger.info(">>> OCRUtils.extract_text 开始执行")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = pdf_file.read()
            if not content:
                raise ValueError("上传的 PDF 文件内容为空。")
            temp_file.write(content)
            temp_pdf_path = temp_file.name

        logger.info(f"[阶段] PDF 已保存为临时文件: {temp_pdf_path}")

        doc = fitz.open(temp_pdf_path)
        logger.info(f"[阶段] 成功打开 PDF，共 {len(doc)} 页")

        full_text = ""
        for i in range(min(len(doc), max_pages)):
            logger.info(f"[阶段] 处理第 {i+1} 页")
            page = doc.load_page(i)

            t0 = time.time()
            pix = page.get_pixmap(dpi=self.dpi)
            logger.info(f"[耗时] get_pixmap 耗时: {time.time() - t0:.2f}s")

            img_path = f"temp_page_{i}.png"
            pix.save(img_path)

            logger.info(f"[阶段] 开始 OCR 识别：{img_path}")
            t1 = time.time()
            page_text = ""

            if self.backend == "paddle":
                result = self.ocr_model.ocr(img_path, cls=True)
                page_text = "\n".join(
                    [line[1][0] for block in result for line in block]
                )
            elif self.backend == "easyocr":
                result = self.ocr_model.readtext(img_path)
                page_text = "\n".join([text for (_, text, _) in result])

            logger.info(f"[耗时] OCR 推理耗时: {time.time() - t1:.2f}s")

            full_text += f"\n--- Page {i + 1} ---\n{page_text}"

            if not self.keep_images:
                try:
                    os.remove(img_path)
                except Exception as e:
                    logger.warning(f"删除临时图片失败: {e}")

        try:
            os.remove(temp_pdf_path)
        except Exception as e:
            logger.warning(f"删除临时 PDF 失败: {e}")

        logger.info(
            f"[总耗时] extract_text 完成，总耗时: {time.time() - start_time:.2f}s"
        )
        return full_text.strip()
