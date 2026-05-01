"""Model-specific parameters for the OpenAI Responses API."""


def responses_api_supports_temperature(model_name: str) -> bool:
    """Some frontier / reasoning models reject the ``temperature`` parameter on ``responses.create``."""
    m = model_name.strip().lower()
    if m.startswith("gpt-5"):
        return False
    if m.startswith("o1") or m.startswith("o3") or m.startswith("o4"):
        return False
    return True
