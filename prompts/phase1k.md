# Phase 1K: World Refinement and Consistency Check: {BATCH_NAME} - {BATCH_ID}

## Instructions for LLM

- Review the outputs from all previous phases (1A through 1J).
- Execute all steps in this prompt in order, providing comprehensive responses for each.
- Complete all steps in a single reply.
- For each step, return the specific outputs requested.
- If you generate any content that doesn't fit into the existing structure, include it in an 'Additional Notes' section at the end of your response.

## Overview

This phase focuses on refining the world elements and ensuring consistency across all aspects of the created world.

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

1. **Consistency Check**
   - Identify any inconsistencies or contradictions in the world elements.
   - **Output**: List any inconsistencies found, and for each, provide:
     - The inconsistent elements
     - The nature of the inconsistency
     - A proposed resolution

2. **Element Refinement**
   - Refine and enhance key world elements to increase depth and coherence.
   - **Output**: For 3-4 world elements, provide:
     - The element being refined
     - The refinement or enhancement made
     - The reason for this refinement

3. **Gap Identification**
   - Identify any gaps in the world-building that need to be addressed.
   - **Output**: List 2-3 areas where more detail or development is needed, including:
     - The area needing development
     - Why it's important to address this gap
     - Suggestions for how to fill this gap

4. **World Cohesion**
   - Evaluate how well the different aspects of the world fit together.
   - **Output**: A paragraph assessing the overall cohesion of the world, highlighting strengths and areas for improvement.

5. **Integration with Core Concept**
   - Reflect on how the refinements and consistency checks relate to the core concept and themes established in Phase 1A.
   - **Output**: A paragraph explaining how these refinements reinforce or adjust the fundamental aspects of your world.

6. **Change History**
   - Document any significant changes or decisions made during this phase.
   - **Output**: A list of any major alterations to the world elements, including the rationale behind each change.

7. **Generate Structured List**
   - Before writing the list, write: "%%% LIST START %%%"
   - Using the refinement and consistency information you've created, organize it into a structured text list format.
   - After writing the list, write: "%%% LIST END %%%"
   - After completing this step, write: "Phase 1K Complete. Output:"

Your response should only include the output from step 7 and should start like this:
%%% LIST START %%%

- World Refinement and Consistency:
  - Consistency Check:
    - Inconsistency 1:
      - Elements: [Inconsistent elements]
      - Nature: [Description of inconsistency]
      - Resolution: [Proposed resolution]
    ...
