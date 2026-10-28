# Jarvis companion conversation

Managed patch of the installed Extended OpenAI Conversation agent. Copy conversation.py and dialogue.py into that integration, then restart HA. Preserve the original file revision for rollback. Upstream/HACS updates can overwrite this managed customization; re-review upstream changes before reapplying.

The agent keeps follow-up listening enabled for ordinary answers, not only questions. Exact Czech stop expressions are intercepted before model/tool execution. Same-device context can be resumed for15min only if no explicit conversation ID was provided. Up to32turns/20min of follow-ups and16storedsessions are retained; turn count is independent of context truncation. Audio silence/timeouts still follow the native satellite. This is turn-based continued conversation, not full-duplex Realtime or guaranteed arbitrary barge-in.

Companion instructions are appended to existing user instructions, preserving device permission/confirmation requirements and prohibiting invented shared ChatGPT memory. Existing OpenAI STT/Onyx are preserved. Native local-intent interception is disabled only for the specifically managed Jarvis pipeline so follow-ups and stop phrases reach the same agent. Sensitive transcript INFO logging is lowered to DEBUG.

The diagnostic integration runs a synthetic text-only recall/stop test after activation. It does not execute household actions or play audio. The final microphone-follow-up and interruption behavior must be tested physically. Direct policy tests and actual agent-method boundary tests cover statements, stop-vs-film-ending, explicit session IDs, and bounded continuation despite truncated history.
