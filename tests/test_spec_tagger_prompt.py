import pytest
import json
from pathlib import Path
from enum import Enum
from src.Prompts import SpecTaggerPrompt, Qualification

# Define paths relative to the project root
TEST_DIR = Path(__file__).parent
PROJECT_ROOT = TEST_DIR.parent
OCR_RESULTS_DIR = PROJECT_ROOT / "ocr_results"
PROMPT_TEMPLATES_DIR = PROJECT_ROOT / "src" / "Prompts" / "MarkdownPrompts"
SUPPORTING_DOCS_DIR = PROMPT_TEMPLATES_DIR / "SupportingDocs"

# Verify that required files exist for testing
AS_LEVEL_SPEC_PATH = SUPPORTING_DOCS_DIR / "AS-Level-Spec-2015.md"
A2_LEVEL_SPEC_PATH = SUPPORTING_DOCS_DIR / "A2-Level-Spec-2015.md"
TAGGER_INSTRUCTIONS_PATH = PROMPT_TEMPLATES_DIR / "specAreaTagger.md"

# Load the spec tagger prompt template once
with open(TAGGER_INSTRUCTIONS_PATH, 'r', encoding='utf-8') as f:
    SPEC_TAGGER_CONTENT = f.read().strip()

# Load AS Level specification content
with open(AS_LEVEL_SPEC_PATH, 'r', encoding='utf-8') as f:
    AS_LEVEL_SPEC_CONTENT = f.read().strip()

# Load A2 Level specification content
with open(A2_LEVEL_SPEC_PATH, 'r', encoding='utf-8') as f:
    A2_LEVEL_SPEC_CONTENT = f.read().strip()

# Sample test data
SAMPLE_QUESTION = """
1. (a) Describe the fetch-execute cycle. [6]

(b) Explain how pipelining improves the performance of a processor. [4]

(c) Describe how branch prediction and speculative execution improve the efficiency of a processor. [5]
"""

SAMPLE_MARK_SCHEME = """
1. (a) Award 1 mark for each valid point made, up to a maximum of 6 marks:
- Fetch phase: instruction retrieved from memory at the address stored in the program counter
- Instruction placed in instruction register
- Program counter incremented to point to next instruction
- Decode phase: instruction is decoded to determine the operation
- Execute phase: the instruction is executed by the ALU
- Result written to register or memory location

(b) Award 1 mark for each valid point made, up to a maximum of 4 marks:
- Pipelining divides instruction processing into stages
- Different stages can be executed simultaneously on different instructions
- Increases throughput of instructions
- Example: while one instruction is being executed, the next can be decoded and a third fetched

(c) Award 1 mark for each valid point made, up to a maximum of 5 marks:
- Branch prediction attempts to guess which way a branch will go before it is executed
- Speculative execution executes instructions along the predicted path before knowing if the branch will be taken
- If prediction is correct, execution continues without delay
- If prediction is wrong, pipeline must be flushed and correct branch loaded
- Modern processors use sophisticated algorithms based on history to improve prediction accuracy
"""


@pytest.fixture
def spec_tagger_prompt_as_level():
    """Fixture that creates a SpecTaggerPrompt instance for AS Level"""
    return SpecTaggerPrompt(
        question=SAMPLE_QUESTION,
        qualification=Qualification.AS_LEVEL,
        mark_scheme=SAMPLE_MARK_SCHEME
    )


@pytest.fixture
def spec_tagger_prompt_a2_level():
    """Fixture that creates a SpecTaggerPrompt instance for A2 Level"""
    return SpecTaggerPrompt(
        question=SAMPLE_QUESTION,
        qualification=Qualification.A2_LEVEL,
        mark_scheme=None  # Test without mark scheme
    )

@pytest.fixture
def spec_tagger_prompt_with_context():
    """Fixture that creates a SpecTaggerPrompt instance with question context"""
    return SpecTaggerPrompt(
        question=SAMPLE_QUESTION,
        qualification=Qualification.AS_LEVEL,
        mark_scheme=SAMPLE_MARK_SCHEME,
        questionContext="This question relates to CPU architecture and optimization techniques."
    )


def test_spec_tagger_prompt_initialization():
    """Test that the SpecTaggerPrompt can be initialized with valid parameters"""
    # Skip if supporting files don't exist
    if not (AS_LEVEL_SPEC_PATH.exists() and TAGGER_INSTRUCTIONS_PATH.exists()):
        pytest.skip(f"Required files missing: {AS_LEVEL_SPEC_PATH} or {TAGGER_INSTRUCTIONS_PATH}")
    
    prompt = SpecTaggerPrompt(
        question=SAMPLE_QUESTION,
        qualification=Qualification.AS_LEVEL,
        mark_scheme=SAMPLE_MARK_SCHEME
    )
    
    assert prompt is not None
    assert prompt.question == SAMPLE_QUESTION
    assert prompt.qualification == Qualification.AS_LEVEL
    assert prompt.mark_scheme == SAMPLE_MARK_SCHEME


def test_spec_tagger_prompt_system_prompt_as_level(spec_tagger_prompt_as_level):
    """Test that the system prompt for AS Level contains correct specification content"""
    # Skip if supporting files don't exist
    if not (AS_LEVEL_SPEC_PATH.exists() and TAGGER_INSTRUCTIONS_PATH.exists()):
        pytest.skip(f"Required files missing: {AS_LEVEL_SPEC_PATH} or {TAGGER_INSTRUCTIONS_PATH}")
    
    system_prompt = spec_tagger_prompt_as_level.get_system_prompt()
    
    # Check that the system prompt contains the AS Level specification title
    assert "# AS-Level Specification" in system_prompt
    
    # Check that the system prompt contains content from the specification file
    # Let's check for a specific line that should be in the AS-Level spec
    assert "Contemporary processor design" in system_prompt or "Architecture" in system_prompt
    
    # Check that the system prompt contains the tagger instructions
    assert "tags exam questions with specification content areas" in system_prompt or "specification points" in system_prompt


def test_spec_tagger_prompt_system_prompt_a2_level(spec_tagger_prompt_a2_level):
    """Test that the system prompt for A2 Level contains correct specification content"""
    # Skip if supporting files don't exist
    if not (A2_LEVEL_SPEC_PATH.exists() and TAGGER_INSTRUCTIONS_PATH.exists()):
        pytest.skip(f"Required files missing: {A2_LEVEL_SPEC_PATH} or {TAGGER_INSTRUCTIONS_PATH}")
    
    system_prompt = spec_tagger_prompt_a2_level.get_system_prompt()
    
    # Check that the system prompt contains the A2 Level specification title
    assert "# A2-Level Specification" in system_prompt
    
    # Read a small portion of the A2 Level specification to check if it's included
    if A2_LEVEL_SPEC_PATH.exists():
        with open(A2_LEVEL_SPEC_PATH, 'r', encoding='utf-8') as f:
            # Read the first 500 characters to find some distinguishing text
            spec_sample = f.read(500)
            # Check if some text from this sample is in the system prompt
            assert any(line in system_prompt for line in spec_sample.splitlines() if line.strip())


def test_spec_tagger_prompt_content_prompt_with_mark_scheme(spec_tagger_prompt_as_level):
    """Test that the content prompt contains question and mark scheme when provided"""
    # Skip if supporting files don't exist
    if not AS_LEVEL_SPEC_PATH.exists():
        pytest.skip(f"Required file missing: {AS_LEVEL_SPEC_PATH}")
    
    content_prompt = spec_tagger_prompt_as_level.get_content_prompt()
    
    # Check that the content prompt contains the question heading and content
    assert "# Question to Tag:" in content_prompt
    assert "Describe the fetch-execute cycle" in content_prompt
    
    # Check that the content prompt contains the mark scheme heading and content
    assert "# Mark Scheme to Tag:" in content_prompt
    assert "Award 1 mark for each valid point made" in content_prompt

def test_spec_tagger_prompt_with_context(spec_tagger_prompt_with_context):
    """Test that the content prompt includes question context when provided"""
    content_prompt = spec_tagger_prompt_with_context.get_content_prompt()
    
    # Check that the context is included and in correct order
    assert "# Question Context:" in content_prompt
    assert "CPU architecture and optimization techniques" in content_prompt
    
    # Verify order of sections
    context_pos = content_prompt.find("# Question Context:")
    question_pos = content_prompt.find("# Question to Tag:")
    mark_scheme_pos = content_prompt.find("# Mark Scheme to Tag:")
    
    assert context_pos < question_pos < mark_scheme_pos


def test_spec_tagger_prompt_content_prompt_without_mark_scheme(spec_tagger_prompt_a2_level):
    """Test that the content prompt contains only question when mark scheme is not provided"""
    # Skip if supporting files don't exist
    if not A2_LEVEL_SPEC_PATH.exists():
        pytest.skip(f"Required file missing: {A2_LEVEL_SPEC_PATH}")
    
    content_prompt = spec_tagger_prompt_a2_level.get_content_prompt()
    
    # Check that the content prompt contains the question heading and content
    assert "# Question to Tag:" in content_prompt
    assert "Describe the fetch-execute cycle" in content_prompt
    
    # Check that the content prompt does not contain mark scheme heading
    assert "# Mark Scheme to Tag:" not in content_prompt


def test_spec_tagger_prompt_combined_prompt(spec_tagger_prompt_as_level):
    """Test that the combined prompt contains both system and content prompts"""
    # Skip if supporting files don't exist
    if not AS_LEVEL_SPEC_PATH.exists():
        pytest.skip(f"Required file missing: {AS_LEVEL_SPEC_PATH}")
    
    combined_prompt = spec_tagger_prompt_as_level.get_combined_prompt()
    system_prompt = spec_tagger_prompt_as_level.get_system_prompt()
    content_prompt = spec_tagger_prompt_as_level.get_content_prompt()
    
    # Check that the combined prompt contains both system and content prompts
    assert system_prompt in combined_prompt
    assert content_prompt in combined_prompt
    
    # Check that the system prompt comes before the content prompt
    system_prompt_pos = combined_prompt.find(system_prompt)
    content_prompt_pos = combined_prompt.find(content_prompt)
    assert system_prompt_pos < content_prompt_pos


def test_spec_tagger_prompt_invalid_qualification():
    """Test that using an invalid qualification raises an error"""
    with pytest.raises((FileNotFoundError, AttributeError)):
        # Create an invalid qualification value that's not a proper Qualification enum
        SpecTaggerPrompt(
            question=SAMPLE_QUESTION,
            qualification="Invalid-Level"  # This should cause an error since it's not a Qualification enum
        )


def test_file_existence():
    """Test that required files exist for the SpecTaggerPrompt to function"""
    # Check that specification files exist
    assert AS_LEVEL_SPEC_PATH.exists(), f"AS Level specification file not found at: {AS_LEVEL_SPEC_PATH}"
    assert A2_LEVEL_SPEC_PATH.exists(), f"A2 Level specification file not found at: {A2_LEVEL_SPEC_PATH}"
    
    # Check that tagger instructions file exists
    assert TAGGER_INSTRUCTIONS_PATH.exists(), f"Spec tagger instructions file not found at: {TAGGER_INSTRUCTIONS_PATH}"


# Sample questions data for testing generateQuestionContext
SAMPLE_QUESTIONS = [
    {
        "question_number": "1a",
        "question_text": "Explain the role of MOD in the algorithm above.",
        "mark_scheme": "- MOD checks if the number is divisible by 2 / calculates the remainder of the inputted number.\n- If the result of modulus is 0 then the number can be divided by 2 and is an even number.\n- If the modulus is not exactly 0 , then the number is not exactly divisible by 2 , hence it will be odd number.",
        "max_marks": 3,
        "assessment_objectives": [
            "AO2.1b"
        ],
        "media_files": []
    },
    {
        "question_number": "1b",
        "question_text": "Using an example from the algorithm, describe the purpose of selection.",
        "mark_scheme": "- Example: if num MOD $2=0$ Then\n- Selection outputs num & \" is an even number\" if the condition num MOD $2=0$ is met.",
        "max_marks": 2,
        "assessment_objectives": [
            "AO2.1b"
        ],
        "media_files": []
    },
    {
        "question_number": "1c",
        "question_text": "Using an example from the algorithm, describe the purpose of repetition.",
        "mark_scheme": "- Example: for i = 1 To numberstocheck\n- Repetition checks if numbers are even/odd until all numbers have been checked.",
        "max_marks": 2,
        "assessment_objectives": [
            "AO2.1b"
        ],
        "media_files": []
    }
]

def test_generate_question_context_without_markscheme(spec_tagger_prompt_as_level):
    """Test that generateQuestionContext correctly formats questions without mark schemes"""
    # Skip if supporting files don't exist
    if not AS_LEVEL_SPEC_PATH.exists():
        pytest.skip(f"Required file missing: {AS_LEVEL_SPEC_PATH}")
    
    context = spec_tagger_prompt_as_level.generateQuestionContext(
        questions=SAMPLE_QUESTIONS,
        include_markscheme=False
    )
    
    # Check that the context contains all question numbers
    assert "Question 1a" in context
    assert "Question 1b" in context
    assert "Question 1c" in context
    
    # Check that question text is included
    assert "Explain the role of MOD in the algorithm above." in context
    assert "Using an example from the algorithm, describe the purpose of selection." in context
    assert "Using an example from the algorithm, describe the purpose of repetition." in context
    
    # Check that mark schemes are NOT included
    assert "MOD checks if the number is divisible by 2" not in context
    assert "Mark Scheme:" not in context


def test_generate_question_context_with_markscheme(spec_tagger_prompt_as_level):
    """Test that generateQuestionContext correctly formats questions with mark schemes"""
    # Skip if supporting files don't exist
    if not AS_LEVEL_SPEC_PATH.exists():
        pytest.skip(f"Required file missing: {AS_LEVEL_SPEC_PATH}")
    
    context = spec_tagger_prompt_as_level.generateQuestionContext(
        questions=SAMPLE_QUESTIONS,
        include_markscheme=True
    )
    
    # Check that the context contains all question numbers
    assert "Question 1a" in context
    assert "Question 1b" in context
    assert "Question 1c" in context
    
    # Check that question text is included
    assert "Explain the role of MOD in the algorithm above." in context
    
    # Check that mark schemes ARE included
    assert "Mark Scheme:" in context
    assert "MOD checks if the number is divisible by 2" in context
    assert "Example: if num MOD $2=0$ Then" in context
    assert "Example: for i = 1 To numberstocheck" in context


def test_generate_question_context_with_current_question_number(spec_tagger_prompt_as_level):
    """Test that generateQuestionContext correctly includes the current question number when provided"""
    # Skip if supporting files don't exist
    if not AS_LEVEL_SPEC_PATH.exists():
        pytest.skip(f"Required file missing: {AS_LEVEL_SPEC_PATH}")
    
    context = spec_tagger_prompt_as_level.generateQuestionContext(
        questions=SAMPLE_QUESTIONS,
        include_markscheme=True,
        current_question_number="1"
    )
    
    # Check that the current question number is included
    assert "Current Question: 1" in context
    
    # Check that other elements are still present
    assert "Question 1a" in context
    assert "Mark Scheme:" in context