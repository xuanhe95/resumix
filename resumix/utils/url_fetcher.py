import requests
import chardet
from readability import Document
from bs4 import BeautifulSoup
from resumix.utils.logger import logger
import trafilatura


class UrlFetcher:
    @staticmethod
    def fetch(url: str, timeout: int = 10) -> str:
        logger.info(f"[WebExtract] 开始抓取 URL: {url}")

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }

        try:
            # Step 1: 网页抓取
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            logger.info(f"[WebExtract] 状态码: {response.status_code}")

            # Step 2: 自动检测编码
            detected = chardet.detect(response.content)
            encoding = detected["encoding"] or "utf-8"
            logger.info(f"[WebExtract] 检测编码: {encoding}")

            html = response.content.decode(encoding, errors="replace")

            # Step 3: 使用 readability 提取正文
            try:
                doc = Document(html)
                summary_html = doc.summary()
                text = BeautifulSoup(summary_html, "html.parser").get_text(
                    separator="\n", strip=True
                )

                if text and len(text.split()) > 30:
                    logger.info(
                        f"[WebExtract] 使用 readability 提取成功，字符数：{len(text)}"
                    )
                    return text
                else:
                    logger.warning(
                        "[WebExtract] readability 提取内容为空或过短，尝试使用 trafilatura"
                    )
            except Exception as e:
                logger.warning(f"[WebExtract] readability 提取失败: {e}")

            # Step 4: fallback 到 trafilatura 提取
            try:
                extracted = trafilatura.extract(
                    html, include_comments=False, include_tables=False
                )
                if extracted:
                    logger.info(
                        f"[WebExtract] 使用 trafilatura 提取成功，字符数：{len(extracted)}"
                    )
                    return extracted.strip()
                else:
                    logger.warning("[WebExtract] trafilatura 也未能提取有效正文")
            except Exception as e:
                logger.error(f"[WebExtract] trafilatura 提取失败: {e}")

        except requests.RequestException as e:
            logger.error(f"[WebExtract] 请求异常: {e}")
        except Exception as e:
            logger.error(f"[WebExtract] 未知异常: {e}")

        return ""
