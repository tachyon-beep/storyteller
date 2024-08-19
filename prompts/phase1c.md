# Phase 1C: Historical Timeline: {BATCH_NAME} - {BATCH_ID}

## Instructions for LLM

- Review the outputs from Phase 1A: Core Concept and Phase 1B: Physical World.
- Execute all steps in this prompt in order, providing comprehensive responses for each.
- Complete all steps in a single reply.
- For each step, return the specific outputs requested.
- If you generate any content that doesn't fit into the existing structure, include it in an 'Additional Notes' section at the end of your response.

## Overview

This phase develops a historical timeline for our story world, establishing key events, eras, and developments that have shaped the world into its current state.

## Previous Content

<CONTENT>
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:A}
{OUTPUT:STAGE:WORLD_BUILDING:PHASE:B}
</CONTENT>

## Additional Guidance

<STAGE_GUIDANCE>
{GUIDANCE:TYPE:STAGE:WORLD_BUILDING}
</STAGE_GUIDANCE>

<GENERAL_GUIDANCE>
{GUIDANCE:TYPE:GENERIC}
</GENERAL_GUIDANCE>

## Instructions

Complete the following steps in order:

1. **Historical Eras**
   - Define 3-5 distinct historical eras for your world.
   - **Output**: For each era, provide:
     - Name of the era
     - Approximate timespan
     - Key characteristics or developments

2. **Pivotal Events**
   - Identify 5-7 pivotal events that have significantly shaped your world.
   - **Output**: For each event, provide:
     - Name of the event
     - When it occurred (which era and approximate date if applicable)
     - Brief description of the event
     - Immediate and long-term consequences

3. **Cultural Evolution**
   - Describe how cultures and societies have evolved over time.
   - **Output**: A paragraph explaining major cultural shifts, including changes in beliefs, practices, or social structures.

4. **Technological or Magical Progression**
   - Outline the development of technology or magic in your world.
   - **Output**: A timeline of 3-5 major technological or magical advancements, including:
     - Name of the advancement
     - When it occurred
     - Its impact on society

5. **Conflicts and Resolutions**
   - Detail major conflicts that have occurred in your world's history.
   - **Output**: Description of 2-3 significant conflicts, including:
     - Parties involved
     - Cause of the conflict
     - Outcome and lasting effects

6. **Legacy of the Past**
   - Explain how historical events continue to influence the present day.
   - **Output**: A list of 3-4 ways in which past events or eras directly impact the current state of the world.

7. **Historical Figures**
   - Introduce 2-3 important historical figures who have left a lasting mark on your world.
   - **Output**: For each figure, provide:
     - Name
     - Era they lived in
     - Their significant contributions or actions
     - Their lasting legacy

8. **Mysteries or Debates**
   - Present 1-2 historical mysteries or debated events that intrigue the current inhabitants of your world.
   - **Output**: For each mystery or debate, describe:
     - The uncertain event or question
     - Why it remains unresolved
     - Its significance to the present day

9. **Generate Structured List**
   - Before writing the list, write: "%%% LIST START %%%"
   - Using the historical information you've created, organize it into a structured text list format. Follow these guidelines:
     - Use indentation to show hierarchy (use spaces, not tabs)
     - Use bullet points (- ) for list items
     - Use clear, descriptive labels for each section
     - Ensure all information from previous steps is included
   - After writing the list, write: "%%% LIST END %%%"
   - After completing this step, write: "Phase 1C Complete. Output:"

Your response should only include the output from step 9 and should start like this:
%%% LIST START %%%

- Historical Timeline:
  - Historical Eras:
    - Era 1:
      - Name: [Era name]
      - Timespan: [Approximate timespan]
      - Key Characteristics: [Brief description]
    ...
