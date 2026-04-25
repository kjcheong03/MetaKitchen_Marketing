from .config import PERSONA_FILE


def load_persona() -> str:
    return PERSONA_FILE.read_text(encoding="utf-8")
