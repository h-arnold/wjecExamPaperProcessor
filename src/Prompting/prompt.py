from pathlib import Path
from typing import List

class Prompt:
    """
    A class to construct a prompt by concatenating a set of strings or markdown files.

    Attributes:
        sources (List[str]):
            A list of strings to be concatenated into a prompt.

    """

    def __init__(self, sources: List[str]):
        """
        Initialise the Prompt object.

        Args:
            sources (Dict[str, Union[str, Path]]):
                Dictionary with values that are either literal strings or paths to markdown files.
        """
        self.sources = sources
        self._prompt = self._build_prompt()

    def _build_prompt(self) -> str:
        """
        Process the list and concatenate all text contents in order.

        Returns:
            str: The concatenated prompt text.
        """
        prompt_parts = []

        for value in self.sources:
            if not isinstance(value, str):
                raise ValueError(f"Error: '{value}' is not a string. All entries in the list must be strings.")
            prompt_parts.append(value.strip())

        return "\n\n".join(prompt_parts)

    def get(self) -> str:
        """
        Retrieve the concatenated prompt string.

        Returns:
            str: The final combined prompt.
        """
        return self._prompt

    def __str__(self):
        return self.get()
