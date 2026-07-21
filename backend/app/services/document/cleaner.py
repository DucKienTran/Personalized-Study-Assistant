# app/services/document/cleaner.py

import re

from app.services.document.constants import (
    MAX_CONSECUTIVE_NEWLINES,
    UNICODE_REPLACEMENTS,
)


class DocumentCleaner:
    """
    Clean extracted document text before chunking.

    Responsibilities:
    - Normalize unicode characters
    - Normalize line endings
    - Remove duplicated spaces
    - Collapse blank lines
    - Remove empty page separators
    - Trim leading/trailing whitespace

    NOTE:
    This class MUST NOT:
    - classify documents
    - split chunks
    - detect headings
    """

    _multiple_spaces_pattern = re.compile(r"[ ]{2,}")
    _multiple_newlines_pattern = re.compile(rf"\n{{{MAX_CONSECUTIVE_NEWLINES + 1},}}")

    _page_separator_pattern = re.compile(
        r"^\s*---\s*Trang\s+\d+\s*---\s*$",
        flags=re.IGNORECASE | re.MULTILINE,
    )

    _empty_line_pattern = re.compile(r"^[ \t]+$", flags=re.MULTILINE)

    def clean(self, text: str) -> str:
        """
        Execute the entire cleaning pipeline.

        Parameters
        ----------
        text:
            Raw extracted text.

        Returns
        -------
        str
            Cleaned text.
        """

        if not text:
            return ""

        text = self._normalize_unicode(text)
        text = self._normalize_line_endings(text)
        text = self._remove_page_markers(text)
        text = self._remove_empty_whitespace_lines(text)
        text = self._collapse_spaces(text)
        text = self._collapse_blank_lines(text)

        return text.strip()

    # ==========================================================
    # Cleaning Steps
    # ==========================================================

    def _normalize_unicode(self, text: str) -> str:
        """
        Replace invisible or problematic unicode characters.
        """

        for old, new in UNICODE_REPLACEMENTS.items():
            text = text.replace(old, new)

        return text

    def _normalize_line_endings(self, text: str) -> str:
        """
        Convert Windows/Mac line endings to Unix.
        """

        return text.replace("\r\n", "\n").replace("\r", "\n")

    def _remove_page_markers(self, text: str) -> str:
        """
        Remove page markers inserted by parser.

        Example:

        --- Trang 5 ---

        """

        return self._page_separator_pattern.sub("", text)

    def _remove_empty_whitespace_lines(self, text: str) -> str:
        """
        Remove lines containing only spaces/tabs.
        """

        return self._empty_line_pattern.sub("", text)

    def _collapse_spaces(self, text: str) -> str:
        """
        Collapse multiple consecutive spaces.
        """

        lines: list[str] = []

        for line in text.split("\n"):
            line = self._multiple_spaces_pattern.sub(" ", line)
            lines.append(line.strip())

        return "\n".join(lines)

    def _collapse_blank_lines(self, text: str) -> str:
        """
        Keep at most MAX_CONSECUTIVE_NEWLINES blank lines.
        """

        replacement = "\n" * MAX_CONSECUTIVE_NEWLINES

        return self._multiple_newlines_pattern.sub(replacement, text)
