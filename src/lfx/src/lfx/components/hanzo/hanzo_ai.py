import os
from typing import Any

from langchain_openai import ChatOpenAI
from pydantic.v1 import SecretStr

from lfx.base.models.model import LCModelComponent
from lfx.field_typing import LanguageModel
from lfx.field_typing.range_spec import RangeSpec
from lfx.inputs.inputs import (
    BoolInput,
    DictInput,
    DropdownInput,
    IntInput,
    SecretStrInput,
    SliderInput,
    StrInput,
)
from lfx.log.logger import logger

# The Hanzo AI gateway (api.hanzo.ai) is OpenAI-compatible and fronts EVERY model
# (Zen / DeepSeek / GLM / ...). This is the one backend for all: flow never talks
# to a raw provider SDK — it talks to the gateway, which routes and bills centrally.
HANZO_DEFAULT_BASE_URL = "https://api.hanzo.ai/v1"
HANZO_MODEL_NAMES = ["zen5-pro", "zen5", "zen5-coder", "zen5-flash", "best"]


class HanzoAIModelComponent(LCModelComponent):
    display_name = "Hanzo AI"
    description = "Generate text through the Hanzo AI gateway (api.hanzo.ai) — one backend for every model."
    icon = "Hanzo"
    name = "HanzoAIModel"

    inputs = [
        *LCModelComponent._base_inputs,
        IntInput(
            name="max_tokens",
            display_name="Max Tokens",
            advanced=True,
            info="The maximum number of tokens to generate. 0 or empty means no explicit limit.",
            range_spec=RangeSpec(min=0, max=128000),
        ),
        DictInput(
            name="model_kwargs",
            display_name="Model Kwargs",
            advanced=True,
            info="Extra keyword args forwarded to the gateway (OpenAI-compatible chat params).",
        ),
        DropdownInput(
            name="model_name",
            display_name="Model",
            advanced=False,
            options=HANZO_MODEL_NAMES,
            value=HANZO_MODEL_NAMES[0],
            combobox=True,
            info="A Zen tier or 'best'. Any model id the gateway serves is also accepted.",
        ),
        StrInput(
            name="base_url",
            display_name="Hanzo API Base",
            advanced=True,
            value=HANZO_DEFAULT_BASE_URL,
            info="The OpenAI-compatible /v1 endpoint. Overrides the HANZO_BASE_URL env var.",
        ),
        SecretStrInput(
            name="api_key",
            display_name="Hanzo API Key",
            info="Your Hanzo key. Falls back to the HANZO_API_KEY environment variable.",
            advanced=False,
            required=False,
        ),
        SliderInput(
            name="temperature",
            display_name="Temperature",
            value=0.1,
            range_spec=RangeSpec(min=0, max=2, step=0.01),
            advanced=True,
        ),
        BoolInput(
            name="json_mode",
            display_name="JSON Mode",
            advanced=True,
            info="If True, force the response into a JSON object.",
        ),
    ]

    def build_model(self) -> LanguageModel:  # type: ignore[type-var]
        logger.debug(f"Hanzo AI request with model: {self.model_name}")

        api_key: Any = self.api_key
        if isinstance(api_key, SecretStr):
            api_key = api_key.get_secret_value()
        api_key = api_key or os.getenv("HANZO_API_KEY")

        base_url = self.base_url or os.getenv("HANZO_BASE_URL") or HANZO_DEFAULT_BASE_URL

        model_kwargs = dict(self.model_kwargs or {})
        model_kwargs.pop("api_key", None)  # never let a stray api_key in kwargs override

        output = ChatOpenAI(
            model=self.model_name,
            api_key=api_key,
            base_url=base_url,
            max_tokens=self.max_tokens or None,
            model_kwargs=model_kwargs,
            temperature=self.temperature if self.temperature is not None else 0.1,
            stream_usage=True,
        )
        if self.json_mode:
            output = output.bind(response_format={"type": "json_object"})
        return output
