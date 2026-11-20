# Companion conversation implementation

User explicitly authorized implementing natural ongoing household dialogue without repeated design confirmations.
- Replace punctuation/English-question heuristic with bounded continued listening for Czech conversation.
- Handle exact Czech stop expressions locally before LLM/tools; preserve ordinary mentions of endings.
- Reuse context only for same device within15min, cap32turns/20min and16storedsessions.
- Append companion instructions to existing prompt; do not expand device permissions. Disable native local intent interception so stop/history reach companion consistently.
- Keep tested OpenAI STT and existing Onyx output. Follow-up is turn-based; arbitrary speech interruption/full-duplex is not promised.
- Test policy regressions and full repository, independent review, revision-checked deployment, native config check/restart, actual two-turn conversational test with stop.
