"""
Gemini Manager for Process Project Files Lambda
-------------------------------------------------------------
This file contains functions for interacting with Google's Gemini for the process_project_files_lambda.
"""

import orjson
import os
import base64
import google.generativeai as genai
from loguru import logger
from json_repair import repair_json

# Get API key from environment variable
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)


def send_to_gemini(file_content, file_name, document_category):
    """
    Send file content to Gemini for processing

    Args:
        file_content (bytes or str): The content of the file as bytes (for PDFs) or string
        file_name (str): The name of the file
        document_category (str): The category of the document

    Returns:
        dict: The response from Gemini, or None if an error occurs
    """
    try:
        logger.info(
            f"Sending file to Gemini: {file_name}, Category: {document_category}"
        )

        # Check if the file is a PDF
        is_pdf = file_name.lower().endswith(".pdf")

        if is_pdf:
            # For PDF files, use the file upload API
            from io import BytesIO

            logger.info(f"Processing PDF file: {file_name}")

            # Create a BytesIO object from the file content
            file_bytes = BytesIO(file_content)

            # Encode the PDF as base64
            base64_pdf = base64.b64encode(file_content).decode("utf-8")

            # Create a prompt that includes file metadata
            prompt = """
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
      "scope": "## General Contractor Scope of Work: Airport Office Building Improvements\n\nThis scope defines the responsibilities of the General Contractor (GC) for the Airport Office Building Improvements project, encompassing overall project management, site supervision, safety, and coordination of all trades.\n\n### 1. Project Management & Administration\n* Overall project planning, scheduling, and progress monitoring.\n* Conducting regular site meetings, recording minutes, and distributing to all stakeholders.\n* Maintaining project documentation, including submittals, RFIs, and change orders.\n* Cost control and budget management.\n* Quality control and assurance throughout all phases of construction.\n* Permitting and inspections coordination with local authorities.\n* Close-out procedures, including punch list management, warranty documentation, and final lien releases.\n\n### 2. Site Supervision & Safety\n* Provide full-time, qualified on-site supervision.\n* Implement and enforce a comprehensive project-specific safety plan in accordance with OSHA and all local regulations.\n* Maintain a clean, organized, and secure job site.\n* Provide and manage all temporary facilities including but not limited to offices, restrooms, and storage areas.\n* Implement and manage dust control measures, including dust barriers and temporary partitions as specified in General Requirements.\n\n### 3. Site Logistics & Utilities\n* Management of all site access, deliveries, and waste removal.\n* Coordination with owner to maintain existing utilities during construction, providing interim utilities as required for project continuity.\n* Removal of all abandoned utility lines back to their source as specified.\n\n### 4. General Construction & Coordination\n* Perform all cutting and patching required to seamlessly integrate new construction/demolition with existing finishes, ensuring surfaces match adjacent areas.\n* Provide and install ALL specified wood blocking for the attachment of miscellaneous equipment including, but not limited to, toilet accessories, door hardware, electrical devices, laboratory equipment, grab bars, handrails, casework, and millwork.\n* Protect all existing items shown to remain throughout the construction process.\n* Coordinate all trades (architectural, mechanical, electrical, plumbing, fire protection, technology, etc.) to ensure seamless integration, avoid interferences, and maintain schedule.\n* Field verify all existing dimensions prior to fabrication and installation.\n* Handle all miscellaneous general labor tasks not specific to a particular trade.\n\n### 5. Demolition (General)\n* Supervise and coordinate selective demolition as outlined in architectural, mechanical, electrical, plumbing, fire protection, and technology demolition plans (e.g., A021A, A041A, M011A, E011A, P101A, FP101A, T011A).\n* Ensure structural members are protected from damage during demolition.\n* Coordinate removal and storage of equipment intended for reuse.\n"
    },
    {
      "name_of_trade": "Electrical Contractor",
      "scope": "## Electrical Contractor Scope of Work: Airport Office Building Improvements\n\nThis scope outlines the responsibilities of the Electrical Contractor for the Airport Office Building Improvements project, covering all electrical demolition, new installations, and modifications.\n\n### 1. Demolition\n* Removal of existing electrical wiring, devices, lighting fixtures, and fire alarm devices within all designated demolition areas, as indicated on drawings E011A and E012A.\n* Safe disconnection and removal of all associated conduits and junction boxes in demolished walls/ceilings.\n\n### 2. New Power & Lighting Installation\n* Installation of all new lighting fixtures, power receptacles, and electrical panels as per lighting and power plans E301A, E302A, E201A, and E202A.\n* Upgrading and/or replacement of existing panelboards and disconnects, including all associated wiring and circuit modifications, to meet new load requirements and code.\n* Installation of all necessary conduits, wiring, and raceways for new electrical devices and panels.\n* Ensuring all wire devices are installed at 84\" AFF (Above Finished Floor) or as otherwise specified on drawings.\n* Patching and repairing of refrigerant line covers and associated surfaces as indicated on A101A to ensure a clean finish.\n\n### 3. Critical Systems & Coordination\n* Ensuring continuous power and full operational status for all data, communications, and FAA equipment throughout the construction process.\n* Coordination with the Technology Systems Contractor for power requirements for new low voltage devices (wireless access points, speakers, cameras, Aiphone intercom system) and new rack space in the electrical closet on the 2nd floor (T201A, T202A).\n* Provide necessary power connections for all new mechanical and plumbing equipment.\n\n### 4. Testing & Commissioning\n* Perform all required electrical testing, including circuit continuity, resistance, and voltage checks, to ensure proper operation and code compliance.\n* Provide documentation of all testing results.\n\n### 5. Code Compliance\n* All electrical work shall comply with the National Electrical Code (NEC), Florida Building Code, and all other applicable local and state electrical codes and regulations.\n"
    },
    {
      "name_of_trade": "Plumbing Contractor",
      "scope": "## Plumbing Contractor Scope of Work: Airport Office Building Improvements\n\nThis scope details the responsibilities of the Plumbing Contractor for the Airport Office Building Improvements project, covering all plumbing demolition, new installations, and modifications.\n\n### 1. Demolition\n* Removal of existing plumbing fixtures, including toilets, urinals, sinks, and water fountains, along with associated piping, within all designated demolition areas as shown on drawing P101A.\n* Safe capping or removal of abandoned water and drain lines back to source where required.\n\n### 2. New Fixture Installation\n* Installation of all new toilets, urinals, lavatories, and water coolers as per plumbing plans P201A and P202A.\n* Ensuring proper rough-ins and final connections for all new fixtures to existing sanitary, vent, and hot/cold water lines.\n* Installation of all necessary piping, valves, and fittings for the new plumbing system.\n\n### 3. Code Compliance & Accessibility\n* All plumbing installations shall strictly comply with the Florida Building Code (Plumbing), Florida Accessibility Code, and all other applicable local and state plumbing codes and regulations.\n* Ensure all toilet room configurations, including fixture locations and clearances, meet code-required accessibility standards (e.g., Florida Accessibility Code 606.1 referenced in G100A).\n\n### 4. Testing\n* Perform all necessary pressure testing and leak detection for new and modified plumbing systems to ensure integrity and compliance.\n"
    }
  ]
}"""

            # Initialize Gemini model for multimodal content
            model = genai.GenerativeModel("gemini-2.0-flash")

            # Send it to Gemini with the file
            response = model.generate_content(
                [prompt, {"mime_type": "application/pdf", "data": base64_pdf}]
            )
            response_text = response.text
            json_string_to_parse = ""
            # Attempt to strip Markdown fences if present
            if response_text.strip().startswith(
                "```json"
            ) and response_text.strip().endswith("```"):
                # Remove the leading '```json' and trailing '```'
                # Use rsplit to ensure we remove the last ```, in case ``` appears in the content
                json_string_to_parse = (
                    response_text.strip()[len("```json") :].rsplit("```", 1)[0].strip()
                )
            else:
                # If no markdown fences, assume it's pure JSON
                json_string_to_parse = response_text.strip()

            good_json_string = repair_json(json_string_to_parse)

            # Return the response
            return orjson.loads(good_json_string)
        return None
    except Exception as e:
        logger.error(f"Error sending file to Gemini: {e}")
        return None
