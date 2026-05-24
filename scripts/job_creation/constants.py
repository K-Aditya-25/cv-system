from __future__ import annotations

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_CV_REQUIREMENTS = (
    "No extra user requirements were provided. Tailor the CV to the job description using "
    "the most relevant truthful evidence from the candidate inventory."
)
MAX_COMPILE_PDF_LLM_CALLS = 2
INITIAL_INTAKE_LLM_CALLS = 1
MAX_AUTOMATIC_ONE_PAGE_LLM_CALLS = MAX_COMPILE_PDF_LLM_CALLS - INITIAL_INTAKE_LLM_CALLS
ONE_PAGE_LIMIT = 1
LOCAL_ENV_FILES = [".env.local", ".env"]
PASTE_END_MARKER = "END"
CTRL_Q = "\x11"
LONGER_CV_PATTERNS = [
    "two page",
    "two-page",
    "2 page",
    "2-page",
    "multi page",
    "multi-page",
    "longer cv",
    "long cv",
    "more than one page",
    "more than 1 page",
]
PROJECT_LINK_HOSTS = ("github", "devpost", "kaggle")
ADDITIONAL_INFORMATION_SECTION = "additional_information"
