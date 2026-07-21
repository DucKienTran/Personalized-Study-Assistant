# app/services/document/constants.py

"""
Document Processing Constants

"""


# ==========================================================
# Chunking
# ==========================================================

# Maximum tokens allowed in a chunk.
#
# We intentionally stay well below Gemini's context limit so
# later AI services can combine multiple neighboring chunks.
MAX_CHUNK_TOKENS = 450

# Minimum number of tokens before considering splitting.
MIN_CHUNK_TOKENS = 120

# If a section exceeds this value, it will be split.
MAX_SECTION_TOKENS = 450

# No overlap for V1.
#
# Neighbor retrieval will be used instead.
CHUNK_OVERLAP = 0

# Prefix used when generating chunk IDs.
CHUNK_ID_PREFIX = "chunk_"

# ==========================================================
# Content Types
# ==========================================================

CONTENT_TYPE_TITLE = "title"

CONTENT_TYPE_HEADING = "heading"

CONTENT_TYPE_PARAGRAPH = "paragraph"

CONTENT_TYPE_LIST = "list"

CONTENT_TYPE_TABLE = "table"

CONTENT_TYPE_CODE = "code"

CONTENT_TYPE_FORMULA = "formula"

SUPPORTED_CONTENT_TYPES = {
    CONTENT_TYPE_TITLE,
    CONTENT_TYPE_HEADING,
    CONTENT_TYPE_PARAGRAPH,
    CONTENT_TYPE_LIST,
    CONTENT_TYPE_TABLE,
    CONTENT_TYPE_CODE,
    CONTENT_TYPE_FORMULA,
}

# ==========================================================
# Heading Detection
# ==========================================================

# Common heading keywords.
#
# Regex matching should be case-insensitive.
HEADING_KEYWORDS = (
    "chapter",
    "lesson",
    "unit",
    "part",
    "section",
    "topic",
)

# Maximum heading length.
#
# Longer text is almost certainly a paragraph.
MAX_HEADING_LENGTH = 120

# ==========================================================
# Cleaning
# ==========================================================

# Collapse consecutive blank lines.
MAX_CONSECUTIVE_NEWLINES = 2

# Characters to normalize.
UNICODE_REPLACEMENTS = {
    "\u00a0": " ",  # Non-breaking space
    "\u200b": "",  # Zero-width space
    "\ufeff": "",  # BOM
    "\t": " ",
    "\r": "",
}

# ==========================================================
# Metadata
# ==========================================================

DEFAULT_LANGUAGE = "unknown"

DEFAULT_SUBJECT = None

DEFAULT_SUB_SUBJECT = None

DEFAULT_DIFFICULTY = None


