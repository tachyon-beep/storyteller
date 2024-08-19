# Phase 1M: World Building Final JSON Compilation: {BATCH_NAME} - {BATCH_ID}

## Instructions for LLM

- Review the outputs from all previous world-building phases (1A through 1L).
- Your task is to compile all this information into a single, comprehensive JSON object according to the provided schema.
- Follow these steps in order, providing your output after each step.
- Use only ASCII characters and avoid any special or Unicode characters.

## Additional Guidance

<GENERAL_GUIDANCE>
{GUIDANCE:TYPE:GENERIC}
</GENERAL_GUIDANCE>

<JSON_GUIDANCE>
{GUIDANCE:PLUGIN:JSON}
</JSON_GUIDANCE>

## Previous Content

Here is the content you should compile into the final JSON:

<CONTENT>
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:A}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:B}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:C}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:D}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:E}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:F}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:G}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:H}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:I}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:J}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:K}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:L}
</CONTENT>

## Steps

1. **Input Processing**
   - Review all provided world-building outputs from phases 1A through 1L.
   - Identify all relevant sections and their corresponding content across all phases.
   - After completing this step, write: "Step 1 Complete. All inputs processed."

2. **JSON Structure Creation**
   - Create the basic structure of the JSON object based on the provided schema.
   - Ensure all required properties are included for each section of the world-building data.
   - After completing this step, write: "Step 2 Complete. Comprehensive JSON structure created."

3. **Data Population**
   - For each section of the world-building output, populate the corresponding part of the JSON structure.
   - Ensure that array items meet the minimum and maximum requirements specified in the schema.
   - Convert any kebab-case keys in the input to camelCase in the JSON output.
   - Include the world bible as a single string, summarizing key elements from all phases.
   - After completing this step, write: "Step 3 Complete. All data populated across all world-building aspects."

4. **Validation**
   - Review the populated JSON to ensure it adheres to the schema requirements.
   - Check that all required fields are present and correctly formatted for each world-building aspect.
   - Verify that array lengths meet the specified constraints throughout the entire structure.
   - Ensure that the world bible string provides a comprehensive overview of the world.
   - After completing this step, write: "Step 4 Complete. Comprehensive JSON validated."

5. **Final Output**
   - Present the complete, populated JSON object containing all world-building data from phases 1A through 1L.
   - Use proper JSON formatting with appropriate indentation for readability.
   - Begin your output with "%%% JSON START %%%" on a new line.
   - Immediately following this line, start the JSON object with the opening curly brace {.
   - End your output with a closing curly brace } followed by "%%% JSON END %%%" on a new line.
   - Do not include any schema definitions, empty structures, or explanatory text.
   - Ensure all data from all world-building phases is accurately represented in the JSON.

## Reminders

- Ensure all data from all world-building phases (1A through 1L) is accurately represented in the JSON.
- Maintain the hierarchical structure defined in the JSON schema across all world-building aspects.
- If any required information is missing from the input, use placeholder text like "[Missing Data]" and include a note in the `changeHistory` array.
- If you encounter any ambiguities or difficulties in mapping the input to the JSON structure, make a reasonable interpretation and document your decision in the `changeHistory` array.
- Pay special attention to maintaining consistency across all sections of the world-building data.

## Schema Overview

The JSON should follow this high-level structure:

<SCHEMA>
{SCHEMA:PLUGIN:JSON}
</SCHEMA>

Ensure that your final JSON output adheres to this structure and includes all required properties as specified in the full schema, encompassing all aspects of the world-building process from phases 1A through 1L.

Your response should only include the output from step 5 and should start like this:
%%% JSON START %%%
{
  "storytellerOutput": {
    "version": "1.0.0",
    "phase": "World Building",
    "inputParameters": {
      ...
