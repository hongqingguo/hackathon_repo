from llm.config import (
    get_anthropic_api_key,
    get_gemini_api_key,
    get_llm_provider,
    get_max_retries,
    get_model_name,
    get_temperature,
    get_timeout,
)


def build_chat_model():
    provider = get_llm_provider()
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=get_model_name(),
            google_api_key=get_gemini_api_key(),
            temperature=get_temperature(),
            timeout=get_timeout(),
            max_retries=get_max_retries(),
        )
    if provider == "claude":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=get_model_name(),
            anthropic_api_key=get_anthropic_api_key(),
            temperature=get_temperature(),
            timeout=get_timeout(),
            max_retries=get_max_retries(),
        )

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=get_model_name(),
        temperature=get_temperature(),
        timeout=get_timeout(),
        max_retries=get_max_retries(),
    )
