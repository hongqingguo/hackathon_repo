import os


def has_openai_config() -> bool:
    return bool(
        os.getenv("OPENAI_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("ANTHROPIC_API_KEY")
    )


def get_llm_provider() -> str:
    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    if provider:
        return provider
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        return "gemini"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "claude"
    return "openai"


def get_model_name() -> str:
    provider = get_llm_provider()
    if provider == "gemini":
        return os.getenv("GEMINI_MODEL", os.getenv("GOOGLE_MODEL", "gemini-1.5-flash"))
    if provider == "claude":
        return os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def get_temperature() -> float:
    return float(os.getenv("OPENAI_TEMPERATURE", "0"))


def get_timeout() -> float:
    return float(os.getenv("OPENAI_TIMEOUT", "30"))


def get_max_retries() -> int:
    return int(os.getenv("OPENAI_MAX_RETRIES", "2"))


def get_gemini_api_key() -> str:
    return os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))


def get_anthropic_api_key() -> str:
    return os.getenv("ANTHROPIC_API_KEY", "")
