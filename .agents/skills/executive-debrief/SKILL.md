---
name: executive-debrief
description: Use exclusively when the user provides an end-of-day raw text diary or decision log. Analyze the text using the aviation FORDEC framework (Facts, Options, Risks, Decision, Execution, Check) to uncover cognitive biases and tunnel vision. Do NOT use for financial accounting, employee scheduling, or active operations.
allowed-tools: [google_search_mcp]
---

# Executive Debrief Skill

This skill implements the aviation FORDEC methodology to stress-test decisions recorded in diaries or logs.

## Protocol
1. **Facts**: Extract objective facts from the log, separating them from opinions/assumptions.
2. **Options**: Identify what options were considered or should have been considered.
3. **Risks**: Map the risks associated with each option.
4. **Decision**: Evaluate the decision made.
5. **Execution**: Critique the execution strategy.
6. **Check**: Identify feedback loops or validation checks to monitor outcomes.

Refer to [fordec_principles.md](file:///Users/ringgi/Playground/AI/AGY/Kaggle/Capstone/pg-ai-agy-kaggle-5-day-ai-agents-capstone/.agents/skills/executive-debrief/references/fordec_principles.md) for detailed Crew Resource Management and decision-making stress-test principles.
