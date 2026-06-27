import os


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DATA_DIR = os.getenv(
    "DATA_DIR",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "data", "documents"),
)
os.makedirs(DATA_DIR, exist_ok=True)

PREVIEW_DPI = 150
EXPORT_DPI = 300

OCR_LANG = os.getenv("OCR_LANG", "en")
OCR_GPU = _env_bool("OCR_GPU", False)
