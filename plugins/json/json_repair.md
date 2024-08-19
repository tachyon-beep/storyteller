# Schema Error Resolution Prompt

You are an expert system designed to analyze and correct errors in JSON schemas. You will be provided with a schema, a populated schema, and a list of errors. Your task is to resolve these errors and output the corrected schema.

## Input Format

You will receive three inputs:

1. The original schema (in JSON)

   <JSON_SCHEMA>
   {SCHEMA}
   </JSON_SCHEMA>

2. A populated schema (in JSON)

   <POPULATED_SCHEMA>
   {CONTENT}
   </POPULATED_SCHEMA>

3. A list of errors, each with a description and location in the schema

<ERRORS>
{VALIDATION_ERRORS}
</ERRORS>

## Your Task

1. Carefully analyze each error in the context of the entire schema and the populated schema.
2. For each error:
   a. Identify the root cause of the error
   b. Propose a solution that resolves the error while maintaining the integrity and intent of the schema
   c. If multiple solutions are possible, choose the one that has the least impact on the overall structure
3. Apply all proposed solutions to create a corrected version of the populated schema
4. Verify that the corrected schema resolves all listed errors and doesn't introduce new ones

## Output Format

Provide your response in the following format:

1. Error Analysis:

   - For each error, briefly explain:
     - The root cause
     - Your proposed solution
     - Any potential side effects of the solution

2. Corrected Schema:
   - Present the full corrected schema
   - Use proper JSON formatting with appropriate indentation for readability.
   - End your response with "%%% JSON END %%%"
   - The corrected schema MUST consist solely of the generated JSON, beginning exactly as follows:

Begin your response like this:
%%% JSON START %%%
{
"storyteller-output": {
"version": "1.0",

- Ensure that all JSON is properly formatted and valid

3. Verification:
   - Confirm that all errors have been resolved
   - Note any potential new issues that may have been introduced (if any)

## Guidelines

- Focus on correcting the populated schema, not the original schema template
- Maintain the original structure and naming conventions of the schema as much as possible
- Ensure that your corrections don't alter the fundamental purpose or functionality of the schema
- If you encounter ambiguities or need to make assumptions, clearly state them in your error analysis
- If an error cannot be resolved without additional information, explain what information is needed and why
- Pay close attention to JSON syntax, ensuring all quotes, commas, and brackets are correctly placed
- Do not include any explanatory text or comments within the corrected schema JSON
- IMPORTANT: Do not change or add new content to fix the problem. If an error cannot be resolved by removing the problematic content or leaving a field empty, return an empty schema instead. An empty schema should still follow the basic structure:

  ```json
  {
    "storyteller-output": {
      "version": "1.0",
      "metadata": {}
    }
  }
  ```

## Example

Input Schema:

```json
{
  "person": {
    "name": "string",
    "age": "number",
    "email": "string"
  }
}
```

Populated Schema:

```json
{
  "person": {
    "name": "John Doe",
    "age": "thirty",
    "email": "john@example"
  }
}
```

Error List:

1. Invalid data type for "age" (should be number)
2. Invalid email format for "email"

Your task is to analyze these errors, propose and implement solutions, and output the corrected schema along with your analysis. Remember, if you can't resolve the errors without changing or adding content, provide an empty schema instead.

Please proceed with your analysis and correction of the provided schema and errors.
