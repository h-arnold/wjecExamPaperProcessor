# QuestionTagger

The QuestionTagger module provides functionality to analyze WJEC exam questions and match them with the appropriate specification content areas using a Large Language Model (LLM).

## Overview

This tool processes questions from the WJEC exam paper index and uses an LLM to tag each question with the relevant specification areas. It can handle both question papers and mark schemes, and supports the following features:

- Tagging questions with specification references (e.g., 1.1.2, 2.3.1)
- Processing hierarchical question structures (main questions and sub-questions)
- Using question context to improve tagging accuracy
- Validating specification tags for correct format and ordering
- Supporting multiple LLM providers (OpenAI, Mistral, Anthropic)
- Dry-run mode for testing without making API calls

## Installation

The QuestionTagger is part of the WJEC Exam Paper Processor package. No additional installation is required if you have already set up the main project.

## Usage

### Command-Line Interface

The QuestionTagger can be run from the command line using the `main.py` script:

```bash
# Basic usage with default options
python -m src.QuestionTagger.main

# Specify custom input and output paths
python -m src.QuestionTagger.main --input path/to/index.json --output path/to/output.json

# Use a different LLM provider and model
python -m src.QuestionTagger.main --llm-provider mistral --llm-model mistral-medium

# Run in dry-run mode (no API calls)
python -m src.QuestionTagger.main --dry-run
```

### Command-Line Options

- `--input`: Path to input index file (default: `Index/final_index.json`)
- `--output`: Path for output tagged index file (default: input_filename_tagged.json)
- `--llm-provider`: LLM provider to use (default: openai, options: openai, mistral, anthropic)
- `--llm-model`: LLM model to use (default: gpt-4)
- `--dry-run`: Run in dry-run mode (does not make actual API calls)
- `--no-validate`: Disable validation of specification tags
- `--verbose`: Enable verbose logging

### Python API

You can also use the QuestionTagger programmatically in your Python code:

```python
from src.QuestionTagger.question_tagger import QuestionTagger

# Initialize the QuestionTagger
tagger = QuestionTagger(
    indexPath="Index/final_index.json",
    llmProvider="openai",
    llmModel="gpt-4",
    dryRun=False,
    outputPath="Index/final_index_tagged.json",
    validateTags=True
)

# Process the entire index
tagger.processIndex()
```

## Environment Variables

Before using the QuestionTagger, you need to set up an environment variable for your chosen LLM API:

- For OpenAI: `OPENAI_API_KEY`
- For Mistral: `MISTRAL_API_KEY`
- For Anthropic: `ANTHROPIC_API_KEY`

Example:
```bash
export OPENAI_API_KEY=your_api_key_here
```

## Output Format

The QuestionTagger adds a `spec_tags` field to each question in the index, containing an array of specification references. For example:

```json
{
    "question_number": "1",
    "question_text": "Explain the concept of abstraction in computer science.",
    "marks": 4,
    "spec_tags": ["1.1.1", "1.1.2"]
}
```

## Common Issues and Troubleshooting

### Missing API Key

If you encounter an error about a missing API key, make sure you've set the appropriate environment variable for your chosen LLM provider.

### Invalid Tags

If you get warnings about invalid specification tags, check that:
1. The LLM is generating tags in the correct format
2. The specification being used matches the qualification level

### Processing Time

Tagging a large number of questions can take time due to:
- Rate limits on LLM API calls
- The need to process hierarchical question structures
- Time required to analyze complex questions

Consider using the `--test-mode` flag for initial testing.

## Contributing

Contributions to the QuestionTagger are welcome. Please ensure that any changes:
- Maintain British English spelling
- Follow the project's coding standards
- Include appropriate documentation
- Add tests for new functionality

## License

This project is licensed under the [LICENSE] included in the repository.