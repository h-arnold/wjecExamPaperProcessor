import pytest
import json
from pathlib import Path
from src.Prompts import QuestionAndMarkschemeParser

# Define paths relative to the project root
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
OCR_RESULTS_DIR = PROJECT_ROOT / "ocr_results"
PROMPT_TEMPLATES_DIR = PROJECT_ROOT / "src" / "Prompts" / "MarkdownPrompts"

# Load the base template content once
BASE_TEMPLATE_PATH = PROMPT_TEMPLATES_DIR / "questionAndMarkschemeParserPrompt.md"
with open(BASE_TEMPLATE_PATH, 'r', encoding='utf-8') as f:
    BASE_TEMPLATE_CONTENT = f.read().strip()

# Load sample question paper data
QP_SAMPLE_PATH = OCR_RESULTS_DIR / "s23-2500u10-1.json"
with open(QP_SAMPLE_PATH, 'r', encoding='utf-8') as f:
    SAMPLE_QP_CONTENT = json.load(f)

# Load corresponding mark scheme data
MS_SAMPLE_PATH = OCR_RESULTS_DIR / "s23-2500u10-1-ms.json"
with open(MS_SAMPLE_PATH, 'r', encoding='utf-8') as f:
    SAMPLE_MS_CONTENT = json.load(f)

# Load hierarchical index to get start indices
INDEX_PATH = PROJECT_ROOT / "Index" / "hierarchical_index.json"
with open(INDEX_PATH, 'r', encoding='utf-8') as f:
    HIERARCHICAL_INDEX = json.load(f)

# Extract start indices for the specific paper
QP_START_INDEX = HIERARCHICAL_INDEX["subjects"]["Computer Science"]["years"]["2023"]["qualifications"]["AS-Level"]["exams"]["Unit 1"]["documents"]["Question Paper"][0]["question_start_index"]
MS_START_INDEX = HIERARCHICAL_INDEX["subjects"]["Computer Science"]["years"]["2023"]["qualifications"]["AS-Level"]["exams"]["Unit 1"]["documents"]["Mark Scheme"][0]["question_start_index"]


def test_question_and_markscheme_parser_prompt_generation():
    """
    Tests the generation of a prompt using QuestionAndMarkschemeParser with realistic data.
    """
    params = {
        'question_paper_content': SAMPLE_QP_CONTENT,
        'mark_scheme_content': SAMPLE_MS_CONTENT,
        'question_start_index': QP_START_INDEX,
        'mark_scheme_start_index': MS_START_INDEX,
        'current_question_number': 1,
        # Use defaults for current indices (will use start_index values)
    }

    # Instantiate the parser
    parser_prompt = QuestionAndMarkschemeParser(params)
    generated_prompt = parser_prompt.get()
    print("\n--- Generated Prompt (test_question_and_markscheme_parser_prompt_generation) ---")
    print(generated_prompt)
    print("--- End Generated Prompt ---")

    # --- Assertions ---

    # 1. Check if the base template content is present
    assert BASE_TEMPLATE_CONTENT in generated_prompt

    # 2. Check for the Question Paper Content section header
    assert "## Question Paper Content" in generated_prompt

    # 3. Check if content from the correct QP indices (1 and 2) is present
    qp_index_1_marker = f"--- Page Index: {params['question_start_index']} ---"
    qp_index_2_marker = f"--- Page Index: {params['question_start_index'] + 1} ---"
    assert qp_index_1_marker in generated_prompt
    assert qp_index_2_marker in generated_prompt
    # Check for specific text from QP index 1 (s23-2500u10-1.json)
    assert "Answer all questions." in generated_prompt
    assert "| Character (ASCII) |" in generated_prompt
    # Check for specific text from QP index 2 (s23-2500u10-1.json)
    # Use single backslashes as they appear in the source markdown
    assert "Y=(4 \\times 5)+(1 \\times 6)+(5 \\times 3)+(3 \\times 2)" in generated_prompt

    # 4. Check for the Mark Scheme Content section header
    assert "## Mark Scheme Content" in generated_prompt

    # 5. Check if content from the correct MS indices (2 and 3) is present
    ms_index_2_marker = f"--- Page Index: {params['mark_scheme_start_index']} ---"
    ms_index_3_marker = f"--- Page Index: {params['mark_scheme_start_index'] + 1} ---"
    assert ms_index_2_marker in generated_prompt
    assert ms_index_3_marker in generated_prompt
    # Check for specific text from MS index 2 (s23-2500u10-1-ms.json)
    assert "# WJEC GCE AS COMPUTER SCIENCE - UNIT 1" in generated_prompt
    # Use the table header which is present in the actual data
    assert "| Question | Answer | Marks | AO1 | AO2 | AO3 | Total |" in generated_prompt
    # Check for specific text from MS index 3 (s23-2500u10-1-ms.json)
    assert "Control Unit" in generated_prompt
    assert "Arithmetic Logic Unit" in generated_prompt

    # 6. Check for the final instruction line
    expected_final_line = f"Please continue from question number {params['current_question_number']}."
    assert generated_prompt.endswith(expected_final_line)

    # 7. Check overall structure (presence of separators and markdown blocks)
    assert generated_prompt.count("---") >= 4 # Separators between sections
    assert generated_prompt.count("```markdown") == 2 # Markdown code blocks for content

def test_question_and_markscheme_parser_index_out_of_bounds():
    """
    Tests error handling when an index is out of bounds.
    """
    params = {
        'question_paper_content': SAMPLE_QP_CONTENT,
        'mark_scheme_content': SAMPLE_MS_CONTENT,
        'question_start_index': 100, # Invalid index
        'mark_scheme_start_index': 2,
        'current_question_number': 1,
    }

    parser_prompt = QuestionAndMarkschemeParser(params)
    generated_prompt = parser_prompt.get()
    print("\n--- Generated Prompt (test_question_and_markscheme_parser_index_out_of_bounds) ---")
    print(generated_prompt)
    print("--- End Generated Prompt ---")

    # Check that the error message from _extract_markdown_content is included
    assert "Error: Start index 100 is out of bounds" in generated_prompt
    # Check that valid MS content is still included using text actually present
    assert "| Question | Answer | Marks | AO1 | AO2 | AO3 | Total |" in generated_prompt

def test_question_and_markscheme_parser_missing_markdown_key():
    """
    Tests handling when a page object is missing the 'markdown' key.
    """
    # Modify sample QP content to remove markdown key from index 1
    modified_qp_content = json.loads(json.dumps(SAMPLE_QP_CONTENT)) # Deep copy
    if len(modified_qp_content) > QP_START_INDEX and isinstance(modified_qp_content[QP_START_INDEX], dict):
        # Ensure the key exists before trying to delete it
        if 'markdown' in modified_qp_content[QP_START_INDEX]:
            del modified_qp_content[QP_START_INDEX]['markdown']

    params = {
        'question_paper_content': modified_qp_content,
        'mark_scheme_content': SAMPLE_MS_CONTENT,
        'question_start_index': QP_START_INDEX,
        'mark_scheme_start_index': MS_START_INDEX,
        'current_question_number': 1,
    }

    parser_prompt = QuestionAndMarkschemeParser(params)
    generated_prompt = parser_prompt.get()
    print("\n--- Generated Prompt (test_question_and_markscheme_parser_missing_markdown_key) ---")
    print(generated_prompt)
    print("--- End Generated Prompt ---")

    # Check that the error message is included for the problematic index
    assert f"Error: Content at index {QP_START_INDEX} is not in the expected format or missing 'markdown' key." in generated_prompt
    # Check that content from the *next* valid index (QP_START_INDEX + 1) is still included for QP
    # Use single backslashes as they appear in the source markdown
    assert "Y=(4 \\times 5)+(1 \\times 6)+(5 \\times 3)+(3 \\times 2)" in generated_prompt
    # Check that MS content is included normally
    # Use the table header which is present in the actual data
    assert "| Question | Answer | Marks | AO1 | AO2 | AO3 | Total |" in generated_prompt

def test_question_and_markscheme_parser_missing_required_param():
    """
    Tests that ValueError is raised if required parameters are missing.
    """
    params = {
        # Missing 'question_paper_content'
        'mark_scheme_content': SAMPLE_MS_CONTENT,
        'question_start_index': 1,
        'mark_scheme_start_index': 2,
    }
    with pytest.raises(ValueError, match="Missing required parameters: question_paper_content"):
        QuestionAndMarkschemeParser(params)

