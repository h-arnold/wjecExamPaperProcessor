"""
QuestionTagger module for tagging exam questions with specification areas.

This module provides functionality to analyze exam questions and match them with
the appropriate specification content areas using an LLM.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple

from ..Prompts.spec_tagger_prompt import SpecTaggerPrompt, Qualification
from ..Llm_client.factory import LLMClientFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


class QuestionTagger:
    """
    A class that processes exam questions and uses an LLM to tag them with 
    specification areas.
    
    This class iterates through questions in the WJEC exam paper index,
    generates prompts using SpecTaggerPrompt, and uses an LLM to identify 
    the relevant specification areas for each question.
    
    Attributes:
        indexPath (Path): Path to the index.json file
        llmClient (LLMClient): LLM client instance for making API calls
        logger (logging.Logger): Logger instance for tracking progress
        qualificationMap (Dict): Mapping between index qualification names and Qualification enum
        dryRun (bool): If True, don't make actual API calls (for testing)
        outputPath (Optional[Path]): Path to save the updated index
        validateTags (bool): Whether to validate specification tags
    """
    
    def __init__(
        self, 
        indexPath: Union[str, Path], 
        llmProvider: str = "openai",
        llmModel: str = "gpt-4.1-mini", # We'll use OpenAI models here because the prompt for the question tagging is very long and they enable prompt caching by default.
        dryRun: bool = False,
        outputPath: Optional[Union[str, Path]] = None,
        validateTags: bool = True
    ):
        """
        Initialize the QuestionTagger with the path to the index file and LLM settings.
        
        Args:
            indexPath (Union[str, Path]): Path to the index.json file
            llmProvider (str): LLM provider name (openai, mistral, etc.)
            llmModel (str): Model name to use
            dryRun (bool): If True, don't make actual API calls (for testing)
            outputPath (Optional[Union[str, Path]]): Path to save the updated index
            validateTags (bool): Whether to validate specification tags
        """
        self.indexPath = Path(indexPath)
        self.logger = logging.getLogger(__name__)
        self.dryRun = dryRun
        self.validateTags = validateTags
        
        # Create LLM client if not in dry run mode
        self.llmClient = None
        if not dryRun:
            try:
                factory = LLMClientFactory()
                self.llmClient = factory.create_client(
                    llmProvider, 
                    model=llmModel
                )
            except Exception as e:
                self.logger.error(f"Failed to create LLM client: {e}")
                raise
        
        # Set output path for the tagged index
        self.outputPath = Path(outputPath) if outputPath else self.indexPath.with_name(
            self.indexPath.stem + "_tagged.json"
        )
        
        # Map qualification names in index to Qualification enum
        self.qualificationMap = {
            "AS-Level": Qualification.AS_LEVEL,
            "A2-Level": Qualification.A2_LEVEL
        }
        
        # Pattern for validating specification tags
        self.specTagPattern = re.compile(r'^\d+(\.\d+)*$')
    
    def _loadIndex(self) -> Dict:
        """
        Load the index JSON file.
        
        Returns:
            Dict: The index data
        
        Raises:
            FileNotFoundError: If the index file doesn't exist
            json.JSONDecodeError: If the index file isn't valid JSON
        """
        try:
            with open(self.indexPath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Index file not found: {self.indexPath}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in index file: {e}")
            raise
    
    def _saveIndex(self, indexData: Dict):
        """
        Save the updated index to the output path.
        
        Args:
            indexData (Dict): The updated index data
        """
        try:
            with open(self.outputPath, 'w', encoding='utf-8') as f:
                json.dump(indexData, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Updated index saved to {self.outputPath}")
        except Exception as e:
            self.logger.error(f"Failed to save updated index: {e}")
            raise
    
    def _validateSpecificationTags(self, tags: List[str]) -> Tuple[bool, str, List[str]]:
        """
        Validate that specification tags follow the expected format and are in ascending order.
        
        The expected format is numbers separated by decimal points, e.g., "1.1.1" or "2.3.4.1".
        Tags should be in ascending order if there are multiple.
        
        Args:
            tags (List[str]): List of specification tags to validate
            
        Returns:
            Tuple[bool, str, List[str]]: A tuple containing:
                - A boolean indicating whether the validation was successful
                - A message describing any validation errors
                - The validated (and possibly corrected) list of tags
        """
        if not tags:
            return False, "No specification tags found", []
        
        # Check that each tag has the correct format
        validatedTags = []
        invalidTags = []
        
        for tag in tags:
            tag = tag.strip()
            if not self.specTagPattern.match(tag):
                invalidTags.append(tag)
            else:
                validatedTags.append(tag)
        
        if invalidTags:
            errorMsg = f"Invalid specification tag format: {', '.join(invalidTags)}"
            self.logger.warning(errorMsg)
            if not validatedTags:
                return False, errorMsg, []
        
        # Check if tags are in ascending order
        sortedTags = sorted(validatedTags, key=lambda x: [int(n) for n in x.split('.')])
        
        if sortedTags != validatedTags:
            self.logger.warning(f"Specification tags were not in ascending order. Original: {validatedTags}, Sorted: {sortedTags}")
            return True, "Tags were reordered to be in ascending order", sortedTags
        
        return True, "Tags validated successfully", validatedTags
    
    def _getSpecificationTags(
        self, 
        questionText: str, 
        qualification: Qualification, 
        markScheme: Optional[str] = None, 
        questionContext: Optional[str] = None
    ) -> List[str]:
        """
        Get specification tags for a question using the LLM.
        
        Args:
            questionText (str): The question text
            qualification (Qualification): The qualification level
            markScheme (Optional[str]): The mark scheme text, if available
            questionContext (Optional[str]): Additional context for the question
        
        Returns:
            List[str]: List of specification tags
        """
        if self.dryRun:
            self.logger.info("Dry run mode - skipping LLM API call")
            return ["1.1.1"]
        
        # Create the prompt
        prompt = SpecTaggerPrompt(
            question=questionText,
            qualification=qualification,
            mark_scheme=markScheme,
            questionContext=questionContext
        )
        
        # Get system and content prompts
        system_prompt = prompt.get_system_prompt()
        content_prompt = prompt.get_content_prompt()
        
        try:
            # Call the LLM
            response = self.llmClient.generate_text(content_prompt, system_prompt)
            
            # Parse the response to extract the specification array
            # The expected format is [1.1.1.2] or [1.1.1.2, 1.2.3.1]
            try:
                # Find the last occurrence of brackets with numbers
                matches = re.findall(r'\[([\d\., ]+)\]', response)
                if matches:
                    # Get the last match (should be the final array)
                    lastMatch = matches[-1]
                    # Split the string by commas and strip whitespace
                    tags = [tag.strip() for tag in lastMatch.split(',')]
                    
                    # Validate tags if configured to do so
                    if self.validateTags:
                        isValid, message, validatedTags = self._validateSpecificationTags(tags)
                        if not isValid and not validatedTags:
                            self.logger.error(f"Tag validation failed: {message}")
                            return []
                        
                        if message != "Tags validated successfully":
                            self.logger.info(f"Tag validation message: {message}")
                        
                        return validatedTags
                    
                    return tags
                else:
                    self.logger.warning(f"No specification tags found in response: {response}")
                    return []
            except Exception as e:
                self.logger.error(f"Failed to parse specification tags: {e}")
                self.logger.error(f"Response was: {response}")
                return []
                
        except Exception as e:
            self.logger.error(f"LLM API call failed: {e}")
            return []
    
    def _processQuestion(
        self, 
        question: Dict, 
        qualification: Qualification, 
        parentContext: Optional[List[Dict]] = None
    ) -> Dict:
        """
        Process a single question to add specification tags.
        
        Args:
            question (Dict): The question data
            qualification (Qualification): The qualification level
            parentContext (Optional[List[Dict]]): Context from parent questions
        
        Returns:
            Dict: The updated question with specification tags
        """
        # Extract question text and mark scheme
        questionText = question.get('question_text', '')
        markScheme = question.get('mark_scheme', '')
        
        # Generate question context if we have parent context
        questionContext = None
        if parentContext:
            contextGenerator = SpecTaggerPrompt(
                question='', 
                qualification=qualification
            )
            questionContext = contextGenerator.generateQuestionContext(
                questions=parentContext,
                include_markscheme=True,
                current_question_number=question.get('question_number', '')
            )
        
        # Get specification tags
        tags = self._getSpecificationTags(
            questionText=questionText,
            qualification=qualification,
            markScheme=markScheme,
            questionContext=questionContext
        )
        
        # Add the tags to the question
        question['spec_tags'] = tags
        
        # Process any subquestions by checking if this is a nested structure
        # with keys like "a", "b", "c" or "i", "ii", "iii" that contain question data
        for key, value in question.items():
            if isinstance(value, dict) and 'question_text' in value:
                # This is a subquestion - get parent context plus current question
                subContext = parentContext.copy() if parentContext else []
                subContext.append(question)
                
                # Process the subquestion
                question[key] = self._processQuestion(
                    question=value,
                    qualification=qualification,
                    parentContext=subContext
                )
        
        return question
    
    def processIndex(self):
        """
        Process the entire index, adding specification tags to all questions.
        """
        # Load the index
        self.logger.info(f"Loading index from {self.indexPath}")
        indexData = self._loadIndex()
        
        # Track progress
        totalQuestions = 0
        processedQuestions = 0
        
        # Iterate through the index structure
        for subjectName, subjectData in indexData.get('subjects', {}).items():
            for year, yearData in subjectData.get('years', {}).items():
                for qualName, qualData in yearData.get('qualifications', {}).items():
                    # Map the qualification name to our enum
                    qualification = self.qualificationMap.get(qualName)
                    if not qualification:
                        self.logger.warning(f"Unknown qualification: {qualName}, skipping")
                        continue
                    
                    # Process each exam in the qualification
                    for unitName, unitData in qualData.get('exams', {}).items():
                        # Process each document type (Question Paper, Mark Scheme)
                        for docType, documents in unitData.get('documents', {}).items():
                            if docType != "Question Paper":
                                continue  # Only process question papers
                            
                            for docIndex, doc in enumerate(documents):
                                # Check if document has questions
                                if 'questions' not in doc:
                                    continue
                                
                                # Count total questions first (for progress reporting)
                                for q in doc['questions']:
                                    totalQuestions += 1
                                
                                # Process each question
                                for qIndex, question in enumerate(doc['questions']):
                                    questionNumber = question.get('question_number', f"Unknown-{qIndex}")
                                    self.logger.info(
                                        f"Processing {subjectName} {year} {qualName} {unitName} "
                                        f"Question {questionNumber} ({processedQuestions+1}/{totalQuestions})"
                                    )
                                    
                                    # Process the question
                                    indexData['subjects'][subjectName]['years'][year]['qualifications'][qualName]['exams'][unitName]['documents'][docType][docIndex]['questions'][qIndex] = self._processQuestion(
                                        question=question,
                                        qualification=qualification
                                    )
                                    
                                    processedQuestions += 1
        
                    # Save the updated index after each exam is processed.
                    self.logger.info(f"Processed {processedQuestions} questions. Saving updated index...")
                    self._saveIndex(indexData)
                    
        
        self.logger.info("Question tagging complete!")
        
def main():
    """
    Main function to run the QuestionTagger on the full index.
    
    To run this function, execute:
    ```
    python -c "from src.QuestionTagger.question_tagger import main; main()"
    ```
    """
    from pathlib import Path
    
    # Path to the index file
    indexPath = Path("Index/final_index.json")
    
    # Create the tagger
    tagger = QuestionTagger(
        indexPath=indexPath,
        llmProvider="openai",
        outputPath=Path("Index/final_index_tagged.json")
    )
    
    # Process the index
    tagger.processIndex()


if __name__ == "__main__":
    # When run as a script, execute the main function
    main()