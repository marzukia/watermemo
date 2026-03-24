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
- recall = true if retrieving past memories about the user would meaningfully help answer this message (personal questions, preferences, context-dependent tasks, anything referencing "me", "my", "I")
- recall = false for generic questions, simple tasks, small talk, or anything where past memories are irrelevant

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
