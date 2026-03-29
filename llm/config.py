import os


def has_openai_config() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def get_model_name() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_temperature() -> float:
    return float(os.getenv("OPENAI_TEMPERATURE", "0"))


def get_timeout() -> float:
    return float(os.getenv("OPENAI_TIMEOUT", "30"))


def get_max_retries() -> int:
    return int(os.getenv("OPENAI_MAX_RETRIES", "2"))
