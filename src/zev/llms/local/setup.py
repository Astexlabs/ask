"""Setup questions for the local provider.

Local mode requires no API keys or configuration, so the questions tuple
is empty.
"""

from typing import Tuple

from zev.config.types import SetupQuestion

questions: Tuple[SetupQuestion, ...] = ()
