from typing import Optional

from PyQt5.QtCore import QRegularExpression
from PyQt5.QtGui import QColor, QFont, QTextCharFormat, QSyntaxHighlighter

from Keywords import KEYWORDS
from Theme import EditorPalette

class PythonHighlighter(QSyntaxHighlighter):
	"""Minimal syntax highlighter for Python code."""

	def __init__(self, document, palette: Optional[EditorPalette] = None) -> None:
		super().__init__(document)
		self.palette = palette or EditorPalette()
		self._rules = []
		self._init_rules()

	def _init_rules(self) -> None:
		def fmt(color: QColor, bold: bool = False, italic: bool = False) -> QTextCharFormat:
			char_format = QTextCharFormat()
			char_format.setForeground(color)
			if bold:
				char_format.setFontWeight(QFont.Weight.Bold)
			if italic:
				char_format.setFontItalic(True)
			return char_format

		keyword_pattern = QRegularExpression(r"\b(" + "|".join(sorted(KEYWORDS)) + r")\b")
		self._rules.append((keyword_pattern, fmt(self.palette.keyword, bold=True)))

		builtin_pattern = QRegularExpression(r"\b(__?[a-zA-Z_]+__?|print|len|range|enumerate|zip|map|filter)\b")
		self._rules.append((builtin_pattern, fmt(self.palette.builtin)))

		number_pattern = QRegularExpression(r"\b(0x[0-9a-fA-F]+|\d+(\.\d+)?)\b")
		self._rules.append((number_pattern, fmt(self.palette.number)))

		string_pattern = QRegularExpression(r"('([^'\\]|\\.)*'|\"([^\"\\]|\\.)*\"|'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\")")
		self._rules.append((string_pattern, fmt(self.palette.string)))

		comment_pattern = QRegularExpression(r"#[^\n]*")
		self._rules.append((comment_pattern, fmt(self.palette.comment, italic=True)))

		function_pattern = QRegularExpression(r"\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)")
		func_format = fmt(self.palette.function)
		func_format.setFontUnderline(True)
		self._rules.append((function_pattern, func_format))

	def highlightBlock(self, text: str) -> None:  # noqa: N802 (Qt API)
		for pattern, text_format in self._rules:
			match_iterator = pattern.globalMatch(text)
			while match_iterator.hasNext():
				match = match_iterator.next()
				start = match.capturedStart()
				length = match.capturedLength()
				if pattern.pattern().startswith("\\bdef") and match.lastCapturedIndex() >= 1:
					# Highlight only the function name capture group.
					start = match.capturedStart(1)
					length = match.capturedLength(1)
				self.setFormat(start, length, text_format)
