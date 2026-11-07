# Jarvis companion conversation

Managed patch of the installed Extended OpenAI Conversation agent. Copy conversation.py, dialogue.py, runtime.py, memory.py and awareness.py into that integration, then restart HA. Preserve the original file revision for rollback. Upstream/HACS updates can overwrite this managed customization; re-review upstream changes before reapplying.

The agent keeps follow-up listening enabled for ordinary answers, not only questions. Exact Czech stop expressions are intercepted before model/tool execution. Same-device context can be resumed for15min only if no explicit conversation ID was provided. Up to32turns/20min of follow-ups and16storedsessions are retained; turn count is independent of context truncation. Audio silence/timeouts still follow the native satellite. This is turn-based continued conversation, not full-duplex Realtime or guaranteed arbitrary barge-in.

Companion instructions are appended to existing user instructions, preserving device permission/confirmation requirements and prohibiting invented shared ChatGPT memory. Existing OpenAI STT/Onyx are preserved. The managed Jarvis pipeline uses local interception disabled so follow-ups and stop phrases reach the same agent. Diagnostics now only observes that setting and never rewrites it. Exact light commands are handled locally inside this agent, before any LLM query. Sensitive transcript INFO logging is lowered to DEBUG.

The diagnostic integration offers an explicitly invoked run_companion_test service for synthetic text-only recall/stop tests; boot no longer contacts the model or rewrites the pipeline. It does not execute household actions or play audio. The final microphone-follow-up and interruption behavior must be tested physically. Direct policy tests and actual agent-method boundary tests cover statements, stop-vs-film-ending, explicit session IDs, and bounded continuation despite truncated history.

## Personality and local memory

Moderate dry sarcasm, factual provenance, natural listening/advice and respectful disagreement are prompt rules. Optional joke suffixes are filtered locally: at least two intervening turns, no similar joke within 30 days, and no joke suffix on serious topics. Family forms of address are Martine, Šarloto, Iris, Petře and Dano. A spoken introduction supplies a session address, never authenticated identity.

`Zapamatuj si: …` stores a dated explicit note. `Zapamatuj si pro domácnost: …` stores a shared note only for an authenticated HA user. `Zapomeň moje poznámky` clears that principal's notes/topics and local history. Verified text users have a private SQLite profile under `jarvis_workspace/companion_memory/`. With the managed speaker identity component, enrolled and conservatively recognized voices have separate durable conversational notes under a random voice enrollment ID; they never access the authenticated HA user's note namespace. Uncertain active voice turns clear guest context and cannot save personal notes. Explicit introductions can provide an address for that turn. Original utterances are retained as topics with dates/sources, not invented summaries. See `managed_sources/speaker_identity/README.md` for enrollment, model limits and deletion. Granular spoken note correction remains future work.

## Device observations

Only explicitly exposed live entities enter the on-turn context. Cooking observations require a supported domain, appliance name and active state with valid timezone-aware last_changed, plus five minutes since first verified observation, at least two conversational turns and a 40-minute cooldown. A situation is offered at most once; refusals suppress it. Direct commands take priority. There is no automatic announcement, background microphone, recipe search or physical action. An entity's absence never proves a device is absent from the home. The current non-smart stove cannot be observed.

The diagnostic snapshot also includes the separately deployed version-scoped native turn-taking controller. It bounds empty follow-up listening to 3 seconds after a statement and 6 after a question, and changes the written name Jarvis to Džárvis only at the targeted non-streamed TTS boundary. It does not implement arbitrary acoustic interruption.

Verification after speaker integration: 24 companion tests, 20 speaker policy/coordinator/hook/transport tests, 2 backend quality tests, 6 diagnostic tests and the repository's complete 159-test suite. Native reports record separate fictional memory, state-observation, identity, actual conversation recall and local-model bridge tests, with their limited scopes.

## Room-relative lights

After “Hey Jarvis” (or during the existing follow-up window), “rozsviť”, “rozsviť to”, “zhasni”, and “zhasni to” target only exposed lights in the microphone device's registered room. An explicit “v koupelně” or “v chodbičce” overrides that source room. Entity area overrides device area for lights. Missing/ambiguous/unknown rooms never target the whole house or fall back to the living room. Text-only clients without a microphone room must name a room. Only exact light forms take this shortcut; complex requests retain the existing agent behavior. Service errors or delayed state updates are never described as verified success.

These words are command intents, not new acoustic wake words. Custom Czech wake words require trained microWakeWord models and firmware validation. The existing model remains Hey Jarvis. Voice identification still requires real enrollment; no text test creates a household profile.
