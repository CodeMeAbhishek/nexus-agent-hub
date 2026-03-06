# Nexus Agent Hub — Improvements & Bugs

Summary of identified **bugs** (fix recommended) and **improvements** (quality, security, UX, consistency).

---

## Bugs

### 1. **Frontend: Settings/Connections API returns full envelope instead of `data`**

**Where:** `src/lib/api.ts` — `getUserSettings()`, `getUserConnections()`

**Issue:** Backend returns `standard_response(data=...)` → `{ success, message, data, error }`. These functions return `res.json()` (the full envelope). Callers expect the payload.

**Impact:**
- **getUserConnections()**: Settings page does `userConnections?.find(c => c.limb_id === limb.id)`. Since `userConnections` is `{ success, message, data, error }`, `.find` is undefined and **all limbs show as disconnected** even when connected.
- **getUserSettings()**: Any consumer expecting `UserSettings` gets the wrong shape.

**Fix:** Unwrap `data` like other endpoints:
```ts
const data = await res.json();
return res.ok ? (data.data ?? null) : null;   // getUserSettings
return res.ok ? (data.data ?? []) : [];      // getUserConnections
```

---

### 2. **Frontend: OAuth exchange success message is wrong**

**Where:** `src/lib/api.ts` — `exchangeGmailToken`, `exchangeCalendarToken`, `exchangeDriveToken`

**Issue:** On success, backend returns `standard_response(data={ message: "Successfully connected to Gmail", success: true })`. So the full body is `{ success, message: "Success", data: { message: "Successfully connected to Gmail", success: true } }`. The frontend does `return { success: true, message: data.message }` → user sees generic **"Success"** instead of **"Successfully connected to Gmail"**.

**Fix:** Use the inner message when present:
```ts
return { success: true, message: data.data?.message ?? data.message ?? "Connected" };
```

---

### 3. **Frontend: Stream API base URL inconsistent**

**Where:** `src/hooks/useAgentStream.ts` line 72

**Issue:** Stream request uses hardcoded `import.meta.env.VITE_API_URL || 'http://localhost:8000'`, while the rest of the app uses `api.ts`’s `BASE` (which also derives from hostname when `VITE_API_URL` is unset). Deployments or custom ports can break streaming.

**Fix:** Use the same base URL as `api.ts`, e.g. export `BASE` from `api.ts` and use it in the hook, or centralize in a small `config.ts`.

---

### 4. **Backend: Rate-limit retry drops chat history**

**Where:** `backend/app/agent/graph.py` — `run_agent()` exception handler (~lines 228–235)

**Issue:** On 429/rate limit, the code retries with `graph.ainvoke({"messages": [HumanMessage(content=query.strip())]})` and **omits `chat_history`**. Context is lost on retry.

**Fix:** Retry with the same `inputs` (including `chat_history`) instead of a fresh messages list with only the latest query.

---

### 5. **Backend: Chat router uses anon Supabase client for history**

**Where:** `backend/app/routers/chat.py` — `_fetch_history()` and `_save_history()` use `get_supabase_client()` (anon key).

**Issue:** Other routes (history, stream) use `get_service_client()` for DB access. With RLS, anon client may not have permission to read/write `chat_sessions` / `chat_messages`, so non-streaming chat history can fail to load or save.

**Fix:** Use `get_service_client()` for fetch/save in the chat router (and ensure session ownership is enforced by your logic or RLS so you don’t expose other users’ data).

---

### 6. **Backend: Stream does not yield “action” events for tool calls**

**Where:** `backend/app/agent/graph.py` — `run_agent_streaming()` astream loop

**Issue:** The loop only yields `"result"` when processing `ToolMessage`. It does not yield an **"action"** event when the agent **starts** a tool call (e.g. “Calling: notion-search”). So the Reasoning Trace shows “Action completed” but not “Calling: …” before it.

**Fix:** When handling `AIMessage` with `tool_calls`, yield an `"action"` event per tool call (e.g. tool name + args summary) before the corresponding `"result"`.

---

## Improvements

### 7. **API response safety for history**

**Where:** `src/lib/api.ts` — `getSessions()`, `getSessionMessages()`

**Issue:** If the backend ever returns `data: null` or a non-array, `data.data` can be `undefined` and cause type/rendering issues.

**Improvement:** Return a safe default: `return data?.data ?? []` (and for getSessionMessages similarly).

---

### 8. **.env.example naming**

**Where:** `backend/.env.example`

**Issue:** Comment says `SUPABASE_SERVICE_KEY`; code uses `SUPABASE_SERVICE_ROLE_KEY`. Docs and code should match.

**Improvement:** Use `SUPABASE_SERVICE_ROLE_KEY` in the example and comments.

---

### 9. **Error response shape for connect/disconnect limb**

**Where:** Backend raises `HTTPException` (FastAPI returns `{ detail: "..." }`); other errors use `error_response()` (`{ message, error: { code, details } }`). Frontend only reads `error.detail`.

**Improvement:** Either use `error_response()` (or a shared helper) for limb connect/disconnect so the frontend can use one shape (e.g. `message` or `error.details`), or have the frontend handle both `detail` and `message`.

---

### 10. **Logging in chat/stream**

**Where:** `backend/app/routers/chat.py`, `backend/app/routers/stream.py`

**Issue:** Failures use `print(...)` or `logging.getLogger(...).error(...)` in a couple of places; the rest of the app uses a module logger.

**Improvement:** Use the same logger pattern everywhere (e.g. `logger = logging.getLogger(__name__)` and `logger.error(...)`) for consistency and log aggregation.

---

### 11. **HITL (Human-in-the-Loop)**

**Where:** Blueprint / Phase 3.3

**Status:** Not implemented. No modal to approve destructive/write actions before execution.

**Improvement:** Add a flow where the agent can emit a “pending action” event, frontend shows an approval modal, and the backend resumes only after approval (or cancellation).

---

### 12. **LangGraph checkpointer + MongoDB (Phase 2.3)**

**Where:** `Project_track_and_logs.md` — 2.3 unchecked

**Status:** Session/task memory across refreshes is not persisted in a checkpointer.

**Improvement:** Add LangGraph checkpointer backed by MongoDB (or existing DB) so the graph state survives page refresh and long sessions.

---

### 13. **Centralize API base URL**

**Where:** Frontend uses `BASE` in `api.ts` and a different base in `useAgentStream.ts`; `AuthContext` builds its own `API_BASE`.

**Improvement:** Single source of truth (e.g. `src/lib/config.ts` or re-export from `api.ts`) and use it for all API and auth calls.

---

### 14. **Auth error handling for history**

**Where:** `getSessions()`, `getSessionMessages()` — on 401/403 they return `[]`.

**Improvement:** Detect 401/403 and trigger logout or redirect to login instead of silently showing “No recent chats”.

---

## Quick reference

| # | Type       | Area        | Summary |
|---|------------|-------------|---------|
| 1 | Bug        | Frontend API| getUserSettings / getUserConnections return full envelope → Settings limbs always disconnected |
| 2 | Bug        | Frontend API| OAuth exchange returns generic “Success” instead of backend message |
| 3 | Bug        | Frontend    | useAgentStream uses hardcoded base URL |
| 4 | Bug        | Backend     | Rate-limit retry drops chat_history |
| 5 | Bug        | Backend     | Chat router uses anon client for history (RLS risk) |
| 6 | Bug        | Backend     | Stream doesn’t yield “action” for tool calls |
| 7 | Improvement| Frontend API| Safe defaults for getSessions / getSessionMessages |
| 8 | Improvement| Backend     | .env.example SUPABASE_SERVICE_ROLE_KEY naming |
| 9 | Improvement| Both        | Consistent error shape for limb connect/disconnect |
| 10| Improvement| Backend     | Consistent logging in chat/stream |
| 11| Improvement| Feature     | HITL approval modal |
| 12| Improvement| Feature     | LangGraph checkpointer + MongoDB |
| 13| Improvement| Frontend    | Single API base URL source |
| 14| Improvement| Frontend    | Auth handling for history (401/403) |
