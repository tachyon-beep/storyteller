# Phase 1L: World Bible Compilation: {BATCH_NAME} - {BATCH_ID}

## Instructions for LLM

- Review the outputs from all previous phases (1A through 1K).
- Execute all steps in this prompt in order, providing comprehensive responses for each.
- Complete all steps in a single reply.
- For each step, return the specific outputs requested.
- If you generate any content that doesn't fit into the existing structure, include it in an 'Additional Notes' section at the end of your response.

## Overview

This phase focuses on compiling all the world-building information into a concise, organized world bible that can be easily referenced in future stages of story creation.

## Previous Content

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

1. **World Overview**
   - Create a concise summary of the world's key features and concepts.
   - **Output**: A paragraph that captures the essence of the world.

2. **Core Elements Summary**
   - Summarize the core elements of the world.
   - **Output**: Brief summaries (1-2 sentences each) of:
     - Physical world
     - History
     - Societal structures
     - Cultural elements
     - Technology/Magic systems
     - Flora and Fauna
     - Languages and Communication

3. **Key Locations**
   - List and briefly describe the most important locations in the world.
   - **Output**: For 3-5 key locations, provide:
     - Name of the location
     - One-sentence description
     - Significance to the world

4. **Major Factions or Groups**
   - Identify the most influential factions or groups in the world.
   - **Output**: For 3-5 major factions, provide:
     - Name of the faction
     - One-sentence description
     - Primary goals or motivations

5. **Central Conflicts**
   - Summarize the main conflicts or tensions in the world.
   - **Output**: List 3-5 central conflicts, each with a brief (one-sentence) description.

6. **Narrative Potential**
   - Highlight key elements with strong narrative potential.
   - **Output**: List 3-5 world elements that offer rich storytelling opportunities, with a brief explanation for each.

7. **World Bible Compilation**
   - Compile all the information from steps 1-6 into a comprehensive world bible.
   - **Output**: A structured document containing all the summarized world information.

8. **Generate Structured List**
   - Before writing the list, write: "%%% LIST START %%%"
   - Using the world bible information you've created, organize it into a structured text list format.
   - After writing the list, write: "%%% LIST END %%%"
   - After completing this step, write: "Phase 1L Complete. World Bible Compiled."

Your response should only include the output from step 8 and should start like this:
%%% LIST START %%%

- World Bible:
  - World Overview: [Your concise world summary]
  - Core Elements:
    - Physical World: [Brief summary]
    - History: [Brief summary]
    ...
