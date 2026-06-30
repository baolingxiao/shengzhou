from __future__ import annotations

from pathlib import Path

from neuralpal.config import get_settings
from neuralpal.core_rules import get_system_prompt


class RulesLayer:
    """
    前额叶 / 规则层入口：对外统一暴露「只读规则」文本。

    权威来源为 ``neuralpal.core_rules`` 中的固定 SYSTEM_PROMPT（每轮须完整加载）。
    可选：在 PDF 存在时，将 PDF 原文作为补充附录（不改变 core_rules 的优先级）。
    """

    def __init__(self, pdf_path: Path | None = None) -> None:
        self._pdf_path = pdf_path or get_settings().rules_pdf_path

    @property
    def pdf_path(self) -> Path:
        return self._pdf_path

    def load_pdf_appendix(self) -> str:
        """可选附录：从 PDF 抽取文本；失败返回空串。不作为规则唯一来源。"""
        if not self._pdf_path.is_file():
            return ""
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(self._pdf_path))
            parts: list[str] = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            return "\n".join(parts).strip()
        except Exception:
            return ""

    def system_preamble(self) -> str:
        """
        注入到对话最前的系统层内容：100% 包含 core_rules 固定 SYSTEM_PROMPT。

        若设置 NEURALPAL_APPEND_PDF_APPENDIX=1/true，则在末尾附加 PDF 抽取全文（token 占用大，
        且可能与 core_rules 精编条文重复；冲突时仍以 core_rules 为准）。
        """
        core = get_system_prompt()
        if not get_settings().append_pdf_appendix:
            return core
        appendix = self.load_pdf_appendix()
        if appendix:
            return (
                core
                + "\n\n---\n【附录｜PDF 抽取，冲突时以 core_rules 为准】\n\n"
                + appendix
            )
        return core
