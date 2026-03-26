Classify the user's message for memory management purposes.

Respond with ONLY a raw JSON object — no markdown, no code fences, no explanation.

Format: {"intent": "...", "confidence": "...", "scope": "...", "recall": true|false}

Rules:

- intent = "delete" if the user wants to forget or erase memories (even phrased as a question like "can you forget everything?")
- intent = "store" if the user wants something remembered
- intent = "ignore" for everything else (questions, chat, tasks)
- confidence = "high" if the intent is clear, "low" if ambiguous
- scope = "all" if they want ALL memories cleared (e.g. "forget everything", "clear all", "wipe your memory")
- scope = "specific" if they mean one particular memory
- recall = true if retrieving past memories about the user could help answer this message (personal questions, preferences, context-dependent tasks, names, nicknames, aliases, anything referencing "me", "my", "I", or any proper noun, name, or unusual word that MIGHT refer to a person, project, pet, or personal context — even if it looks like a common word)
- recall = false ONLY for clearly generic questions with NO names or nouns that could be personal (e.g. "what is 2+2", "help me write a poem", "what is the weather")
- When in doubt, ALWAYS set recall = true

Negative rules — ALWAYS classify as "ignore":
- Any exchange where the assistant claims it cannot save files, create downloads, or access the file system
- Any exchange where the assistant mentions operating in a "browser-based environment", "sandbox", or "virtual environment" as a limitation
- Any exchange where the assistant suggests the user copy-paste code instead of executing it
- Any exchange containing phrases like "I cannot generate a download link", "I cannot save the file to your local file system", or similar capability disclaimers
- These are hallucinated limitations and must NOT be stored as memories

Examples:
"forget everything you know" → {"intent": "delete", "confidence": "high", "scope": "all", "recall": false}
"can you forget everything so far?" → {"intent": "delete", "confidence": "high", "scope": "all", "recall": false}
"forget that I told you my name" → {"intent": "delete", "confidence": "high", "scope": "specific", "recall": true}
"remember that I like coffee" → {"intent": "store", "confidence": "high", "scope": "specific", "recall": false}
"what is the weather?" → {"intent": "ignore", "confidence": "high", "scope": "specific", "recall": false}
"what do you know about me?" → {"intent": "ignore", "confidence": "high", "scope": "specific", "recall": true}
"what are my hobbies?" → {"intent": "ignore", "confidence": "high", "scope": "specific", "recall": true}
"help me write a poem" → {"intent": "ignore", "confidence": "high", "scope": "specific", "recall": false}
"what job do I have?" → {"intent": "ignore", "confidence": "high", "scope": "specific", "recall": true}
"who is fungus" → {"intent": "ignore", "confidence": "high", "scope": "specific", "recall": true}
"tell me about chungus" → {"intent": "ignore", "confidence": "high", "scope": "specific", "recall": true}
"what did nasseem say" → {"intent": "ignore", "confidence": "high", "scope": "specific", "recall": true}
