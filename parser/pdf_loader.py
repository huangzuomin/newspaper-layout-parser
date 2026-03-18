"""
PDF加载器
PDF Loader using PyMuPDF (fitz)
"""

import fitz
from typing import Tuple, Optional
import logging

logger = logging.getLogger("parser")


class PDFLoader:
    """PDF文档加载器"""

    def __init__(self, file_path: str):
        """
        初始化PDF加载器

        Args:
            file_path: PDF文件路径
        """
        self.file_path = file_path
        self.doc: Optional[fitz.Document] = None
        self._open()

    def _open(self):
        """打开PDF文档"""
        try:
            logger.info(f"Loading PDF: {self.file_path}")
            self.doc = fitz.open(self.file_path)
            logger.info(f"PDF loaded successfully: {self.page_count} pages")
        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
            raise

    @property
    def page_count(self) -> int:
        """获取页数"""
        if self.doc is None:
            return 0
        return self.doc.page_count

    def load_page(self, page_no: int) -> fitz.Page:
        """
        加载指定页面

        Args:
            page_no: 页码（0-based）

        Returns:
            fitz.Page对象
        """
        if self.doc is None:
            raise RuntimeError("PDF document not loaded")

        if page_no < 0 or page_no >= self.page_count:
            raise IndexError(f"Page number {page_no} out of range (0-{self.page_count - 1})")

        logger.debug(f"Loading page {page_no}")
        return self.doc[page_no]

    def get_page_dimensions(self, page_no: int) -> Tuple[float, float]:
        """
        获取页面尺寸

        Args:
            page_no: 页码（0-based）

        Returns:
            (width, height) 元组
        """
        page = self.load_page(page_no)
        rect = page.rect
        return rect.width, rect.height

    def get_page_rect(self, page_no: int) -> fitz.Rect:
        """
        获取页面矩形

        Args:
            page_no: 页码（0-based）

        Returns:
            fitz.Rect对象
        """
        page = self.load_page(page_no)
        return page.rect

    def close(self):
        """关闭PDF文档"""
        if self.doc is not None:
            logger.debug("Closing PDF document")
            self.doc.close()
            self.doc = None

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    def __del__(self):
        """析构函数"""
        self.close()
