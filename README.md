# WJEC Exam Paper Processor

## Project Overview

The WJEC Exam Paper Processor is a specialised tool designed to automate the extraction, processing, and analysis of Welsh Joint Education Committee (WJEC) examination papers. This tool helps educators, assessment designers, and educational researchers work more efficiently with exam content by automating metadata extraction and content organization.

## Key Features

- Automated extraction of exam paper metadata (titles, questions, marks, etc.)
- Structured organization of exam content for easier analysis
- Support for various WJEC exam formats across different subject areas
- Tools for comparing exam content across years and specifications
- Export capabilities for further analysis in other systems

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Mistral AI API key

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/examPapersInMarkdown.git
   cd examPapersInMarkdown
   ```

2. Install the required packages:

   ```bash
   pip install mistralai
   ```

3. Set up your Mistral AI API key as an environment variable:

   ```bash
   export MISTRAL_API_KEY="your-api-key"
   ```

   For Windows:

   ```powershell
   set MISTRAL_API_KEY=your-api-key
   ```

4. Create the required directories:

   ```bash
   mkdir -p source_pdfs ocr_results
   ```

## Metadata Extraction

The system extracts crucial metadata from WJEC exam papers including:

- Paper code and reference numbers
- Subject and qualification information
- Date and session information
- Question structure and mark allocation
- Content domain coverage

This metadata enables efficient searching, categorisation and analysis of exam papers.

## Usage

1. Place your PDF files in the `source_pdfs` directory.

2. Run the main script:

   ```bash
   python src/main.py
   ```

3. The OCR results will be saved in the `ocr_results` directory. For each PDF:
   - A JSON file with the OCR text data
   - An images directory containing extracted images (if any)

## Configuration

The application can be configured by modifying the following variables in `main.py`:

- `source_folder`: The directory containing the source PDF files (default: `./source_pdfs`)
- `destination_folder`: The directory where OCR results will be saved (default: `./ocr_results`)
- The OCR model can be changed by modifying the `model` parameter when initializing `MistralOCRClient`

## Output Format

The OCR results are saved as JSON files with the following structure:

```json
[
  {
    "page_number": 1,
    "text": "Extracted text content...",
    "images": [
      {
        "image_path": "relative/path/to/image.jpeg",
        "bounding_box": {
          "x0": 100,
          "y0": 200,
          "x1": 300,
          "y1": 400
        }
      }
    ]
  }
]
```

## Error Handling

The application includes comprehensive logging to help diagnose issues:

- Information messages track the processing progress
- Error messages capture exceptions during processing
- Each file is processed independently, so errors with one file won't affect others

## License

[Add your license information here]

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
