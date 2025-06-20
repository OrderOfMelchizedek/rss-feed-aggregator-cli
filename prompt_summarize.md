Analyze the provided RSS feed list and create a two-part summary following these exact specifications:

**PART 1: TOP 3 MOST IMPORTANT DEVELOPMENTS**
- Identify the three single most important developments from the entire feed
- If the user specifies importance criteria, use those; otherwise, use your judgment based on factors like global impact, breaking news status, geopolitical significance, and potential long-term consequences
- For each development, provide:
  - A descriptive title that captures the essence of the story
  - A substantive paragraph summary (7-10 sentences) using only facts from the provided article descriptions
  - Cite every claim made in-line.
  - Provide a list of the five most relevant articles used to produce the summary. 

**PART 2: THEMATIC SUMMARY OF ALL OTHER HEADLINES**
- Group all other articles (excluding those used for the top 3 developments) into themes based on common topics or subjects.
- Order themes by importance/relevance (most important first). A theme's importance will be proportional to the number of articles used to construct its summary.
- Include only substantial themes that contain enough articles to support its inclusion in the summary (at least 5 articles OR 5% of total articles, whichever is smaller)
- For each theme:
  - Create a clear theme name as a header
  - Write a substantive paragraph summary (5-7 sentences) that synthesizes information from all articles in that theme. Be careful to weave together a coherent narrative rather than simply stating disjointed headlines one after another. 
  - Cite all claims made in the theme's summary in-line.
  - Provide a list of the five most relevant articles used to produce the summary. 
- An article may only appear in one theme; if an article seems like it would be relevant in multiple themes, place it under the most relevant theme.
- Create a "Miscellaneous/Other Developments" section at the end for articles that don't fit substantial themes

**FORMATTING REQUIREMENTS:**
- Use dash separators (---) between all major sections
- Maintain strictly factual, neutral tone throughout
- Base all summaries solely on information provided in the article titles and descriptions. Do not add analysis, opinions, or information from outside sources
- Avoid sweeping generalizations; every statement should be backed up by the underlying articles. Every statement made should be based on an article and cited in-line.
- When identifying patterns or broader context, draw only from the collective content of the provided summaries
- Use direct quotes from key figures where appropriate.
- Weave together a coherent narrative. Rather than merely listing disjointed headlines one after another in paragraph form, embed all the information within the broader context of the news. All summaries should flow seamlessly together and pivots to different topics should be smooth and logically coherent. 


**OUTPUT STRUCTURE:**
```
## TOP 3 MOST IMPORTANT DEVELOPMENTS

1. **[Descriptive Title]**
[Paragraph summary]

Key Articles:
1. Article No. {ARTICLE_NO}: [Shortened title]
2. Article No. {ARTICLE_NO}: [Shortened title]
3. Article No. {ARTICLE_NO}: [Shortened title]
4. Article No. {ARTICLE_NO}: [Shortened title]
5. Article No. {ARTICLE_NO}: [Shortened title]


2. **[Descriptive Title]**  
[Paragraph summary]

Key Articles:
1. Article No. {ARTICLE_NO}: [Shortened title]
2. Article No. {ARTICLE_NO}: [Shortened title]
3. Article No. {ARTICLE_NO}: [Shortened title]
4. Article No. {ARTICLE_NO}: [Shortened title]
5. Article No. {ARTICLE_NO}: [Shortened title]


3. **[Descriptive Title]**
[Paragraph summary]

Key Articles:
1. Article No. {ARTICLE_NO}: [Shortened title]
2. Article No. {ARTICLE_NO}: [Shortened title]
3. Article No. {ARTICLE_NO}: [Shortened title]
4. Article No. {ARTICLE_NO}: [Shortened title]
5. Article No. {ARTICLE_NO}: [Shortened title]

---

## THEMATIC SUMMARY

**[Theme Name 1]**
[Comprehensive paragraph summary of all articles in this theme]

Key Articles:
1. Article No. {ARTICLE_NO}: [Shortened title]
2. Article No. {ARTICLE_NO}: [Shortened title]
3. Article No. {ARTICLE_NO}: [Shortened title]
4. Article No. {ARTICLE_NO}: [Shortened title]
5. Article No. {ARTICLE_NO}: [Shortened title]

---

**[Theme Name 2]**
[Comprehensive paragraph summary of all articles in this theme]

Key Articles:
1. Article No. {ARTICLE_NO}: [Shortened title]
2. Article No. {ARTICLE_NO}: [Shortened title]
3. Article No. {ARTICLE_NO}: [Shortened title]

---

[Continue for all substantial themes...]

---

**Miscellaneous/Other Developments**
[Summary paragraph of remaining articles that don't fit main themes]

Articles:
1. Article No. {ARTICLE_NO}: [Shortened title]
2. Article No. {ARTICLE_NO}: [Shortened title]
```