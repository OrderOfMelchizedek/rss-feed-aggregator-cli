Analyze the provided RSS feed list and create a two-part summary following these exact specifications:

**PART 1: TOP 3 MOST IMPORTANT DEVELOPMENTS**
- Identify the three single most important developments from the entire feed
- If the user specifies importance criteria, use those; otherwise, use your judgment based on factors like global impact, breaking news status, geopolitical significance, and potential long-term consequences
- For each development, provide:
  - A descriptive title that captures the essence of the story
  - A brief paragraph summary (5-7 sentences) using only facts from the provided article descriptions

**PART 2: THEMATIC SUMMARY OF ALL OTHER HEADLINES**
- Group all articles (excluding the top 3) into themes based on common topics or subjects
- Order themes by importance/relevance (most important first)
- Include only substantial themes that contain either:
  - At least 2 articles, OR
  - At least 5% of total articles (rounded down)
  - Whichever is greater
- For each theme:
  - Create a clear theme name as a header
  - Write a substantive paragraph summary (5-7 sentences) that synthesizes information from all articles in that theme. Be careful to weave together a coherent narrative rather than simply stating disjointed headlines one after another. 
  - List the 10 most relevant articles from that theme using shortened titles in a numbered format. Never list the same article twice.
- An article may only appear in one theme; if an article seems like it would be relevant in multiple themes, place it under the most relevant theme.
- Create a "Miscellaneous/Other Developments" section at the end for articles that don't fit substantial themes

**FORMATTING REQUIREMENTS:**
- Use dash separators (---) between all major sections
- Maintain strictly factual, neutral tone throughout
- Base all summaries solely on information provided in the article titles and descriptions
- Do not add analysis, opinions, or information from outside sources
- When identifying patterns or broader context, draw only from the collective content of the provided summaries

**OUTPUT STRUCTURE:**
```
TOP 3 MOST IMPORTANT DEVELOPMENTS

1. [Descriptive Title]
[Paragraph summary]

2. [Descriptive Title]  
[Paragraph summary]

3. [Descriptive Title]
[Paragraph summary]

---

THEMATIC SUMMARY

[Theme Name 1]
[Comprehensive paragraph summary of all articles in this theme]

Articles:
1. [Shortened title]
2. [Shortened title]
3. [Shortened title]

---

[Theme Name 2]
[Comprehensive paragraph summary of all articles in this theme]

Articles:
1. [Shortened title]
2. [Shortened title]

---

[Continue for all substantial themes...]

---

Miscellaneous/Other Developments
[Summary paragraph of remaining articles that don't fit main themes]

Articles:
1. [Shortened title]
2. [Shortened title]
```
