---
description: Research Skill with grounded answers.
---

function research(domain, sources) {
  constraints {
    CRITICAL: When you receive the FIRST user query in a conversation, you MUST fetch ALL sources in a SINGLE fetch_webpage tool call.
    - Pass ALL URLs from sources array to fetch_webpage at once (not one by one).
    - Use a single combined query string that covers all aspects of the user's question.
    - DO NOT make multiple separate fetch_webpage calls for individual URLs.
    - Only after fetching all sources should you analyze and respond.
    - For subsequent queries in the same conversation, you already have the source content and do not need to refetch.
    
    Additional requirements:
    * Ground all answers in actual implementation details from the fetched sources.
    * Be concise and accurate.
    * Cite the specific source URL when providing information.
  }
  
  workflow {
    Step 1: If this is the FIRST query in the conversation, call fetch_webpage ONCE with urls=[all URLs from sources array] and query=<user's question>
    Step 2: Analyze the content from all fetched pages (or use previously fetched content if not the first query)
    Step 3: Formulate and provide the response
  }
}