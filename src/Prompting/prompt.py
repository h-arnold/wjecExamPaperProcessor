from pathlib import Path
from typing import Dict, Union

class Prompt:
    """
    A class to construct a prompt by concatenating a set of strings or markdown files.

    Attributes:
        sources (Dict[str, Union[str, Path]]):
            A dictionary where each value is either:
            - A string (literal content to be included directly), or
            - A path (string or Path object) to a markdown file to be read and included.
    """

    def __init__(self, sources: Dict[str, Union[str, Path]]):
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
        Process the dictionary and concatenate all text contents in order.

        Returns:
            str: The concatenated prompt text.
        """
        prompt_parts = []

        for key, value in self.sources.items():
            if isinstance(value, (str, Path)) and Path(value).is_file():
                # If the value is a path to a markdown file, read the file
                try:
                    content = Path(value).read_text(encoding='utf-8')
                except Exception as e:
                    raise ValueError(f"Error reading file '{value}': {e}")
                prompt_parts.append(content.strip())
            else:
                # Otherwise, assume it's a literal string
                prompt_parts.append(str(value).strip())

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
