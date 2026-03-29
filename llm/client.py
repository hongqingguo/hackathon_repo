from llm.config import get_max_retries, get_model_name, get_temperature, get_timeout


def build_chat_model():
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=get_model_name(),
        temperature=get_temperature(),
        timeout=get_timeout(),
        max_retries=get_max_retries(),
    )
