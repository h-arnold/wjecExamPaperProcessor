# WJEC Exam Paper Metadata Extraction

## Overview

The metadata extraction component is a core feature of the WJEC Exam Paper Processor that automatically identifies and extracts structured information from examination papers. This process transforms unstructured PDF content into organised, searchable data that can be used for analysis and educational planning.

## Extracted Metadata Categories

### Paper Identification

- **Paper Code**: The unique identifier for each exam paper (e.g., C700U20-1)
- **Qualification Name**: GCSE, AS, A Level
- **Subject**: The specific subject area (e.g., Mathematics, English Literature)
- **Component ID**: The specific component or module of the qualification
- **Examination Series**: The year and season (Summer/Winter) of the exam series

### Structural Information

- **Page Count**: Total number of pages in the paper
- **Question Count**: Total number of main questions
- **Sub-question Count**: Total number of sub-questions
- **Total Marks Available**: The maximum possible score for the paper

### Content Analysis

- **Content Domains**: The curriculum areas covered by each question
- **Assessment Objectives**: The specific skills being assessed (e.g., AO1, AO2)
- **Question Types**: Categorisation of questions (e.g., multiple choice, extended response)
- **Mark Distribution**: How marks are allocated across different questions and sections

### Resource Information

- **Included Materials**: Details of formula sheets, data booklets, or other resources provided
- **External References**: Any references to texts or other materials
- **Required Equipment**: Special tools or materials candidates need to use (e.g., calculators)

## Extraction Process

1. **Document Pre-processing**:
   - PDF conversion to machine-readable format
   - Image recognition for diagrams and figures
   - Layout analysis to understand document structure

2. **Text Analysis**:
   - Natural language processing to identify question boundaries
   - Pattern matching for mark allocations
   - Recognition of structural elements (headers, footers, question numbering)

3. **Metadata Classification**:
   - Machine learning models categorise content by assessment objectives
   - Rule-based systems identify paper codes and reference information
   - Content domain mapping based on keyword analysis and context

4. **Validation and Quality Assurance**:
   - Automated checks for metadata completeness
   - Validation against known WJEC formats and structures
   - Anomaly detection for unusual patterns that might indicate extraction errors

## Output Format

The extracted metadata is stored in a structured JSON format that includes:

```json
{
  "paper_id": "C700U20-1",
  "qualification": "GCSE",
  "subject": "Mathematics",
  "series": "Summer 2023",
  "structural_data": {
    "total_marks": 80,
    "total_questions": 12,
    "page_count": 24
  },
  "questions": [
    {
      "question_number": 1,
      "marks": 4,
      "assessment_objectives": ["AO1"],
      "content_domain": "Number",
      "sub_questions": []
    },
    // Additional questions...
  ]
}
```

## Integration Points

The metadata extraction component interfaces with other parts of the system:

- Provides structured data for the content analysis module
- Feeds into the search and filtering functionality
- Supports comparative analysis across different exam papers and years
- Enables custom report generation based on specific metadata categories

## Future Enhancements

Planned improvements to the metadata extraction system include:

- Enhanced recognition of mathematical notation and formulae
- Support for additional language papers (Welsh/English bilingual support)
- Machine learning improvements for more accurate assessment objective classification
- Integration with curriculum mapping tools
