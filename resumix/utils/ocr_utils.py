import os
import time
import tempfile
import fitz  # PyMuPDF
from utils.logger import logger
from io import BytesIO
from resumix.utils.timeit import timeit
from typing import Union
from PIL import Image
import numpy as np


class OCRUtils:
    def __init__(self, ocr_model=None, dpi: int = 100, keep_images: bool = False):
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
        os.environ["FLAGS_use_mkldnn"] = "1"
        os.environ["OMP_NUM_THREADS"] = "4"  # 视 CPU 核心数设置

    def _detect_backend(self):
        if self.ocr_model is None:
            raise ValueError("OCR model cannot be None.")
        if hasattr(self.ocr_model, "ocr"):
            return "paddle"
        elif hasattr(self.ocr_model, "readtext"):
            return "easyocr"
        else:
            raise TypeError("Unsupported OCR model type.")

    @timeit()
    def save_image_stream(self, pix: fitz.Pixmap) -> BytesIO:
        img_stream = BytesIO()
        pix.pil_save(img_stream, format="PNG")
        img_stream.seek(0)
        return img_stream

    @timeit()
    def save_image_disk(self, pix: fitz.Pixmap, path: str):
        pix.save(path)

    @timeit()
    def _perform_ocr_file(self, image_path: str) -> str:
        """
        根据后端类型执行 OCR，并返回提取的文本。
        """
        if self.backend == "paddle":
            result = self.ocr_model.ocr(image_path, cls=True)
            return "\n".join([line[1][0] for block in result for line in block])
        elif self.backend == "easyocr":
            result = self.ocr_model.readtext(image_path)
            return "\n".join([text for (_, text, _) in result])
        else:
            raise ValueError(f"不支持的 OCR 后端类型：{self.backend}")

    @timeit()
    def extract_text(self, pdf_file, max_pages: int = 2) -> str:
        logger.info(">>> OCRUtils.extract_text 开始执行")
        start_time = time.time()

        temp_pdf_path = self._save_pdf_tempfile(pdf_file)
        doc = self._open_pdf(temp_pdf_path)

        full_text = self._process_pages(doc, max_pages)

        self._cleanup_temp_file(temp_pdf_path)

        logger.info(
            f"[总耗时] extract_text 完成，总耗时: {time.time() - start_time:.2f}s"
        )
        return full_text.strip()

    @timeit()
    def _save_pdf_tempfile(self, pdf_file) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            content = pdf_file.read()
            if not content:
                raise ValueError("上传的 PDF 文件内容为空。")
            temp_file.write(content)
            temp_pdf_path = temp_file.name
        logger.info(f"[阶段] PDF 已保存为临时文件: {temp_pdf_path}")
        return temp_pdf_path

    def _open_pdf(self, path: str):
        doc = fitz.open(path)
        logger.info(f"[阶段] 成功打开 PDF，共 {len(doc)} 页")
        return doc

    def _cleanup_temp_file(self, path: str):
        try:
            os.remove(path)
        except Exception as e:
            logger.warning(f"删除临时 PDF 失败: {e}")

    @timeit()
    def _process_pages(self, doc, max_pages: int) -> str:
        full_text = ""
        for i in range(min(len(doc), max_pages)):
            logger.info(f"[阶段] 处理第 {i+1} 页")
            page = doc.load_page(i)

            pix = self._render_page_to_image(page)
            img_path = f"temp_page_{i}.png"
            self.save_image_disk(pix, img_path)

            logger.info(f"[阶段] 开始 OCR 识别：{img_path}")
            t1 = time.time()
            page_text = self._perform_ocr_file(img_path)
            logger.info(f"[耗时] OCR 推理耗时: {time.time() - t1:.2f}s")

            full_text += f"\n--- Page {i + 1} ---\n{page_text}"

            if not self.keep_images:
                self._cleanup_temp_file(img_path)

        return full_text

    @timeit()
    def _render_page_to_image(self, page):
        pix = page.get_pixmap(dpi=self.dpi)
        return pix
