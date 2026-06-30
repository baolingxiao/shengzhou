from __future__ import annotations

import re


class TextChunker:
    """Normalize long CN text and split it into TTS-friendly chunks."""

    _SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[。！？；!?;])")
    _KAOMOJI_PAREN_PATTERN = re.compile(
        r"[\(（][^\)）]{1,48}[\)）][\u0300-\u036f\u00a9\u00ae\u2000-\u3300\udc00-\udfff\u3099-\u30ff\u3040-\u309f]*"
    )

    def __init__(self, *, max_chars: int = 160) -> None:
        self.max_chars = max(40, int(max_chars))

    def strip_for_speech(self, text: str) -> str:
        """Remove kaomoji while keeping punctuation and emoji for TTS."""
        raw = (text or "").strip()
        if not raw:
            return ""

        try:
            from neuralpal.chat.response_signature import _strip_trailing_known_signature

            raw = _strip_trailing_known_signature(raw)
        except Exception:
            pass

        cleaned = self._KAOMOJI_PAREN_PATTERN.sub(
            lambda m: m.group(0) if re.search(r"[\u4e00-\u9fff]", m.group(0)) else "",
            raw,
        )
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        return cleaned.strip()

    def normalize(self, text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return ""

        normalized = re.sub(r"[ \t]+", " ", raw)
        normalized = re.sub(r"\n{2,}", "\n", normalized)
        normalized = normalized.replace("...", "……")
        return normalized.strip()

    def split(self, text: str) -> list[str]:
        normalized = self.normalize(text)
        if not normalized:
            return []

        if len(normalized) <= self.max_chars:
            chunks = [normalized]
        else:
            chunks = []
            for paragraph in normalized.split("\n"):
                sentence_parts = self._SENTENCE_SPLIT_PATTERN.split(paragraph)
                sentence_parts = [s.strip() for s in sentence_parts if s.strip()]
                self._pack_sentences(sentence_parts, chunks)

        spoken: list[str] = []
        for chunk in chunks:
            for line in chunk.split("\n"):
                spoken_line = self.strip_for_speech(line)
                if spoken_line:
                    spoken.append(spoken_line)
        return spoken

    def _pack_sentences(self, sentences: list[str], chunks: list[str]) -> None:
        current = ""
        for sentence in sentences:
            if not current:
                current = sentence
                continue
            candidate = f"{current}{sentence}"
            if len(candidate) <= self.max_chars:
                current = candidate
            else:
                chunks.append(current)
                current = sentence

        if current:
            if len(current) <= self.max_chars:
                chunks.append(current)
                return
            chunks.extend(self._hard_cut(current))

    def _hard_cut(self, text: str) -> list[str]:
        return [text[i : i + self.max_chars] for i in range(0, len(text), self.max_chars)]
