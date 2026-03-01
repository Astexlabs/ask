from typing import Optional

from zev.llms.types import OptionsResponse


class InferenceProvider:
    def __init__(self):
        raise NotImplementedError("Subclasses must implement this method")

    def get_options(self, prompt: str, context: str) -> Optional[OptionsResponse]:
        raise NotImplementedError("Subclasses must implement this method")
