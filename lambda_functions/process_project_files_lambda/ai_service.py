"""
AI Service Module for Process Project Files Lambda
-------------------------------------------------------------
This file contains classes for interacting with AI services (Gemini and OpenAI) for the process_project_files_lambda.
"""

import os
import base64
from io import BytesIO
from abc import ABC, abstractmethod
from loguru import logger

# Import AI-specific libraries
import orjson
import google.generativeai as genai
import openai
from json_repair import repair_json

# Config
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPEN_API_KEY = os.environ.get("OPEN_API_KEY")


class AIService(ABC):
    """Abstract base class for AI services"""

    @abstractmethod
    def process_file(self, file_content, file_name, document_category):
        """
        Process a file with the AI service
        
        Args:
            file_content (bytes or str): The content of the file
            file_name (str): The name of the file
            document_category (str): The category of the document
            
        Returns:
            dict: The analysis result, or None if an error occurs
        """
        pass


class GeminiService(AIService):
    """Class for interacting with Google's Gemini"""

    def __init__(self):
        """Initialize the Gemini service"""
        genai.configure(api_key=GEMINI_API_KEY)
        self.model = genai.GenerativeModel("gemini-2.0-flash")

    def process_file(self, file_content, file_name, document_category):
        """
        Process a file with Gemini
        
        Args:
            file_content (bytes or str): The content of the file
            file_name (str): The name of the file
            document_category (str): The category of the document
            
        Returns:
            dict: The analysis result, or None if an error occurs
        """
        try:
            logger.info(f"Processing file with Gemini: {file_name}, Category: {document_category}")
            
            # Check if the file is a PDF
            is_pdf = file_name.lower().endswith(".pdf")
            
            if is_pdf:
                # Encode the PDF as base64
                base64_pdf = base64.b64encode(file_content).decode("utf-8")
                
                # Create a prompt for PDF analysis
                prompt = self._get_pdf_prompt()
                
                # Send it to Gemini with the file
                response = self.model.generate_content(
                    [prompt, {"mime_type": "application/pdf", "data": base64_pdf}]
                )
                
                # Parse the response
                return self._parse_gemini_response(response.text)
            
            # For now, only handle PDFs
            return None
        except Exception as e:
            logger.error(f"Error processing file with Gemini: {e}")
            return None
    
    def _get_pdf_prompt(self):
        """Get the prompt for PDF analysis"""
        return """
You are an expert construction project manager and document reviewer. Your task is to perform a detailed and thorough analysis of the provided PDF document, which contains architectural, engineering, and/or project specifications.

**Objective:** Extract critical information, identify potential issues, formulate clarifying questions, and define detailed scopes of work for various trades. Your analysis must be extremely meticulous, covering all sections of the document.

**Instructions for Analysis and Output:**

1.  **Deep Dive into Content:**
    * Read every section, table, diagram, and note within the PDF.
    * Identify implicit and explicit requirements, constraints, and dependencies.
    * Pay close attention to details, quantities, materials, methodologies, and cross-references between different sections or drawings (if mentioned).

2.  **Potential Errors/Contradictions Analysis:**
    * **Rigorous Identification:** Actively search for *all* potential errors, ambiguities, conflicts, omissions, inconsistencies, or deviations from best practices, standard codes (e.g., building codes, fire codes, accessibility codes), or typical industry expectations. This includes but is not limited to:
        * Discrepancies between text and referenced drawings/sections.
        * Unrealistic timelines or specifications.
        * Missing information crucial for execution (e.g., finishes, dimensions).
        * Contradictions in material specifications, dimensions, or installation methods.
        * Code violations (mention the code if possible, even if general).
        * Safety concerns.
        * Scope gaps or overlaps.
    * **Categorization (`issue_level`):**
        * `critical`: An issue that will directly prevent project progress, cause significant safety hazards, incur massive rework, or lead to major legal/code violations if not addressed immediately.
        * `warning`: An issue that could lead to delays, cost overruns, quality issues, or minor code violations if not addressed, but doesn't immediately halt the project.
    * **Detailing (`issue_details`):** Provide a concise yet comprehensive description of *what* the issue is, *why* it's an issue, and *what the implication* might be.
    * **Page Number (`page_number`):** Always provide the exact page number(s) where the issue is found. If the issue spans multiple pages or is a result of cross-referencing, list all relevant pages.
    * **Approximate Cost Impact (`approximate_cost`):** Estimate a realistic financial range (e.g., "5,000 - 15,000 USD") for addressing this issue or the potential cost if it's left unaddressed. State "N/A" if truly no cost impact can be estimated.
    * **Delay Impact (`delay`):** Estimate the number of days the project might be delayed if this issue is not resolved promptly. State "0" if no direct delay is anticipated.

3.  **Questions for Further Investigation:**
    * **Probing Questions:** Generate questions that demonstrate a deep understanding of the project and aim to clarify ambiguities, fill information gaps, or resolve identified potential issues. These should be questions a seasoned PM would ask.
    * **Contextual Page Number:** For every question, specify the `page_number` from which the question arose or to which it directly relates. If it's a general question derived from the overall document, state "Overall Document".

4.  **Trade-Specific Scope of Work Identification:**
    * **Comprehensive Coverage:** Identify *all relevant* construction trades required for the project described in the document. Do not limit to just a few; think broadly (e.g., specialized trades, temporary works, clean-up).
    * **Detailed Markdown Scope:** For each identified trade, provide a *highly detailed and comprehensive* scope of work specific to the content of *this particular PDF*. This scope must be in **Markdown format**, using headings, bullet points, and code blocks (if applicable for specs) to clearly organize the information.
        * Break down the scope into logical sub-sections (e.g., Demolition, Installation, Coordination, Testing).
        * Reference specific drawing numbers, sections, or details from the PDF where relevant (e.g., "Installation of new lighting fixtures as per drawing E301A").
        * Include general requirements pertinent to that trade (e.g., safety, quality control, coordination with other trades).
        * The markdown should be structured as if it were a section of a formal Request for Proposal (RFP) or a sub-contractor's scope.

**Output Format:**

Your entire response MUST be a single JSON object. Do NOT include any introductory text, concluding remarks, or extraneous characters outside of the JSON structure. Escape markdown properly so it can be parsed by json.loads

```json
{
  "potential_errors": [
    {
      "issue_level": "critical",
      "issue_details": "Drawing A001A indicates both 'Site Plan (First Floor)' and 'Second Floor Plan'. Site plans should be separate drawings, and the 'Second Floor Plan' should be a dedicated floor plan for the second level, indicating a potential mislabeling or combined drawing issue. This could lead to confusion and incorrect construction on site.",
      "page_number": "A001A (referencing section/drawing label)",
      "approximate_cost": "5,000 - 15,000 USD",
      "delay": "3-5 days"
    },
    {
      "issue_level": "warning",
      "issue_details": "In Life Safety Plan (G100A), occupancy load calculation for Assembly and Business areas on the second floor uses 'Gross' square footage. Occupancy load calculations according to building codes (e.g., IBC Section 1004) should typically be based on NET usable floor area, which can significantly alter the required exit capacities and potentially lead to code violations.",
      "page_number": "G100A",
      "approximate_cost": "2,000 - 8,000 USD",
      "delay": "2-3 days"
    }
  ],
  "questions": [
    {
      "question": "Regarding the elevator finishes, the demolition plan is unclear. Could you provide a detailed specification or schedule for the *final interior finishes* of the elevator post-demolition, including materials, colors, and specific product IDs?",
      "page_number": "Relevant architectural or demolition plan page (e.g., A021A, A041A)"
    },
    {
      "question": "The relocation of electrical equipment is mentioned. Please provide specific drawing references or a marked-up plan indicating the *exact new locations* for all electrical equipment that requires relocation, including any necessary conduit or wiring reroutes.",
      "page_number": "Relevant electrical plan page (e.g., E011A, E012A, E201A)"
    }
  ],
  "trade_requirements": [
    {
      "name_of_trade": "General Contractor",
      "scope": "## General Contractor Scope of Work..."
    },
    {
      "name_of_trade": "Electrical Contractor",
      "scope": "## Electrical Contractor Scope of Work..."
    },
    {
      "name_of_trade": "Plumbing Contractor",
      "scope": "## Plumbing Contractor Scope of Work..."
    }
  ]
}
```
"""
    
    def _parse_gemini_response(self, response_text):
        """Parse the response from Gemini"""
        try:
            # Attempt to strip Markdown fences if present
            if response_text.strip().startswith("```json") and response_text.strip().endswith("```"):
                # Remove the leading '```json' and trailing '```'
                json_string_to_parse = response_text.strip()[len("```json"):].rsplit("```", 1)[0].strip()
            else:
                # If no markdown fences, assume it's pure JSON
                json_string_to_parse = response_text.strip()
            
            # Repair and parse the JSON
            good_json_string = repair_json(json_string_to_parse)
            return orjson.loads(good_json_string)
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
            return None


class OpenAIService(AIService):
    """Class for interacting with OpenAI"""

    def __init__(self):
        """Initialize the OpenAI service"""
        self.client = openai.OpenAI(api_key=OPEN_API_KEY)
        self.model = "gpt-4o-mini"

    def process_file(self, file_content, file_name, document_category):
        """
        Process a file with OpenAI
        
        Args:
            file_content (bytes or str): The content of the file
            file_name (str): The name of the file
            document_category (str): The category of the document
            
        Returns:
            dict: The analysis result, or None if an error occurs
        """
        try:
            logger.info(f"Processing file with OpenAI: {file_name}, Category: {document_category}")
            
            # Check if the file is a PDF
            is_pdf = file_name.lower().endswith(".pdf")
            
            if is_pdf:
                # Create a BytesIO object from the file content
                file_bytes = BytesIO(file_content)
                
                # Create a prompt for PDF analysis
                prompt = self._get_pdf_prompt(file_name, document_category)
                
                # Send it to OpenAI with the file
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI assistant that processes and analyzes files. You will analyze the provided PDF document.",
                        },
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:application/pdf;base64,{file_bytes}"
                                    },
                                },
                            ],
                        },
                    ],
                    temperature=0.7,
                )
                
                # Return the response
                return {
                    "file_name": file_name,
                    "document_category": document_category,
                    "analysis": response.choices[0].message.content,
                }
            else:
                # For text files, decode the bytes to string if needed
                if isinstance(file_content, bytes):
                    try:
                        file_content = file_content.decode("utf-8")
                    except UnicodeDecodeError:
                        logger.error(f"Failed to decode file content as UTF-8: {file_name}")
                        return None
                
                # Create a prompt for text analysis
                prompt = self._get_text_prompt(file_name, document_category, file_content)
                
                # Send it to OpenAI
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AI assistant that processes and analyzes files.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                )
                
                # Return the response
                return {
                    "file_name": file_name,
                    "document_category": document_category,
                    "analysis": response.choices[0].message.content,
                }
        except Exception as e:
            logger.error(f"Error processing file with OpenAI: {e}")
            return None
    
    def _get_pdf_prompt(self, file_name, document_category):
        """Get the prompt for PDF analysis"""
        return f"""
Process the following PDF file:
Filename: {file_name}
Category: {document_category}

Please analyze this file and provide insights based on its content and category.

respond back with JSON 
JSON example:
{{
"potential_errors": ["Give list of potential errors or any contradictory information in the file"],
"questions": ["Give the list of questions if you have any for further investigations"],
"trade_requirements": ["Give all list of trade requirements based on this document"],
}}
"""
    
    def _get_text_prompt(self, file_name, document_category, file_content):
        """Get the prompt for text analysis"""
        return f"""
Process the following file:
Filename: {file_name}
Category: {document_category}

File Content:
{file_content}

Please analyze this file and provide insights based on its content and category.
"""


class AIServiceFactory:
    """Factory class for creating AI services"""
    
    @staticmethod
    def get_service(service_type="gemini"):
        """
        Get an AI service based on the service type
        
        Args:
            service_type (str): The type of AI service to use (gemini or openai)
            
        Returns:
            AIService: An instance of the requested AI service
        """
        if service_type.lower() == "openai":
            return OpenAIService()
        else:
            return GeminiService()