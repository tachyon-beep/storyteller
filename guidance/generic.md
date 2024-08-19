# General Storytelling Guidance for Synthetic Data Generation

This guidance provides overarching principles and best practices applicable to all stages of the storytelling process, with a focus on creating diverse synthetic data for LLM training.

## General Guidelines

1. Maintain consistency within each snippet, including characters, plot, setting, and themes.
2. Create vivid and engaging foundations that leave room for imaginative expansion.
3. Balance specificity with flexibility to allow for creative interpretation.
4. Incorporate a broad spectrum of linguistic styles, vocabulary levels, and narrative techniques.
5. Generate content that spans different cultural contexts, historical periods, and speculative futures.
6. Consider the interplay between different aspects of the world and how they influence each other.
7. Prioritize diversity in all aspects of storytelling: genres, settings, characters, plots, and themes.
8. Include both common and uncommon storytelling elements to ensure a rich training dataset.
9. Vary the complexity of narratives, from straightforward to intricate, to create a range of training examples.

## Managing Incongruity

When you encounter elements that seem incongruous or difficult to reconcile within a story snippet:

1. Use creative reinterpretation to reimagine incongruous elements so they naturally fit within the story's world.
2. Consider creating unique aspects of the world that explain the presence of seemingly out-of-place elements.
3. Explore genre blending, creating unique settings that naturally accommodate diverse elements.
4. Use narrative framing devices to allow for the inclusion of disparate elements when necessary.
5. Acknowledge incongruity through character reactions, adding depth to the world and characters.

Remember:

- Prioritize the integrity of the core narrative within each snippet.
- Aim for subtle integrations that don't overshadow the main story.
- If an element proves impossible to integrate satisfyingly, consider replacing it with something more congruent.
- Incongruity can be a valuable tool for creating unique and memorable narratives when handled skillfully.

## Handling Changes in Story Data

When refining story elements across multiple snippets:

1. Ensure each snippet stands alone as a coherent piece of narrative.
2. Allow for deliberate variations in style, setting, and character across different snippets to increase diversity.
3. When revisiting similar themes or settings, introduce new perspectives or elements to enhance variety.
4. Focus on creating a wide range of distinct story elements rather than maintaining continuity between snippets.
5. Use metadata tags to categorize snippets by their attributes (genre, style, content warnings, etc.) for easy reference and analysis.

## Diversity and Inclusion Considerations

1. Create characters with diverse backgrounds, identities, and experiences.
2. Incorporate a variety of cultural practices, beliefs, and worldviews into the snippets.
3. Represent different family structures, relationships, and social dynamics.
4. Include characters with diverse abilities and body types.
5. Showcase a range of professions, socioeconomic backgrounds, and education levels.

## Content Variety

1. Generate snippets that represent different parts of a story: beginnings, middles, climaxes, and resolutions.
2. Include a mix of dialogue-heavy and description-rich snippets.
3. Create snippets that focus on character development, world-building, and plot advancement.
4. Incorporate various literary devices: foreshadowing, flashbacks, metaphors, etc.
5. Generate content that spans different reading levels and target age groups.

## Ethical Considerations

1. Include ethical dilemmas and complex situations to provide nuanced training data.
2. Represent diverse viewpoints while avoiding the promotion of harmful ideologies positively.

## Pacing and Emotional Tone Implementation

1. Review the pacing and emotional tone specified for your world.
2. For the given pacing (e.g., fast-paced, measured, varied):
   - Consider how this pacing might manifest in different aspects of your world (e.g., technological advancement, cultural change, political shifts).
   - Think about how the pacing affects the rhythm of daily life in your world.
   - Identify elements in your world that either reinforce or create tension with this pacing.
3. For the specified emotional tone (e.g., hopeful, melancholic, tense):
   - Identify aspects of your world that contribute to this overall tone.
   - Consider how this tone might be reflected in architecture, art, or cultural practices.
   - Think about potential contrasts or variations in tone across different parts of your world.
4. Ensure that your pacing and emotional tone choices are consistent with your genre framework and themes.
5. Consider how pacing and tone might vary across different narrative moments or locations within your world.

## Balancing Genre Conventions and Subversions

1. Identify 3-5 key conventions of your chosen genre(s).
2. For each convention:
   - Decide whether to play it straight, subvert it, or offer a unique interpretation.
   - If subverting, explain your approach and its potential impact on the narrative.
   - If playing it straight, consider how to make it feel fresh or unique in your world.
3. Look for opportunities to blend conventions from different genres in interesting ways.
4. Ensure that any subversions or unique interpretations serve a purpose in your overall narrative and world-building.
5. Consider how your approach to genre conventions might surprise or engage the audience.
6. Maintain a balance between familiar genre elements and innovative twists to create a satisfying yet original world.
7. Ensure consistency in how conventions are treated across multiple world-building phases.
8. Consider how subversions in one aspect of the world might affect other areas, maintaining logical coherence.

## Phase Integration

1. Regularly cross-reference information from previous phases when developing new aspects of the world.
2. Ensure that new elements introduced in later phases align with and enhance earlier established concepts.
3. Use a consistent system for tracking and organizing information across all phases.
4. When contradictions arise between phases, carefully consider which elements to modify to maintain overall coherence.
5. Look for opportunities to create meaningful connections between elements developed in different phases.

## Scope Management

1. For each world aspect, determine its significance to potential narratives and character development.
2. Prioritize detailed development of elements most likely to impact future storytelling.
3. For less critical elements, establish broad concepts that can be expanded if needed later.
4. Regularly assess whether the level of detail being developed is appropriate for the story's needs.
5. Be prepared to adjust the scope of world-building as the process reveals new narrative possibilities.

## Output

1. Please respond using only ASCII characters and avoid any special or Unicode characters.
2. If you have additional notes that are valuable, but are not able to be stored in the JSON schema, you may use create an additional notes section. Notes should be in the format:
<example_note>
[Stage] - [Note]
</example_note>

## Reminders

- Aim for concise, impactful content within each snippet. Keep individual descriptions under 200 words unless more detail is necessary.
- Ensure that all elements within a snippet are consistent with each other and support the overall narrative and atmosphere.
- Before finalizing any snippet, review the content to ensure it forms a cohesive, engaging, and logically consistent narrative.
- Focus on creating self-contained snippets that can stand alone as coherent pieces of narrative.
- Regularly review the generated content to ensure overall diversity and quality across the dataset.

Remember, the goal is to create a rich, diverse dataset of storytelling snippets that will provide comprehensive training data for LLMs, enabling them to generate varied and high-quality narrative content while adhering to established storytelling principles.
