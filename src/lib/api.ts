/**
 * Nexus Agent Hub — API client for backend (FastAPI).
 * Uses VITE_API_URL if set; otherwise same host as the page on port 8000
 * so 127.0.0.1:8080 → http://127.0.0.1:8000 (avoids localhost vs 127.0.0.1 mismatch).
 */
const BASE =
  import.meta.env.VITE_API_URL ??
  (typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : "http://localhost:8000");

export interface ApiLimb {
  id: string;
  name: string;
  status: "active" | "disconnected";
  tools_count: number;
}

export interface ListToolsResponse {
  limbs: ApiLimb[];
  total_tools: number;
}

const API_TIMEOUT_MS = 15_000;

export async function listTools(): Promise<ListToolsResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    const res = await fetch(`${BASE}/api/tools`, {
      signal: controller.signal,
      headers: getAuthHeaders()
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    const data = await res.json();
    return data.data;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  const data = await res.json();
  return data.data;
}

export interface ChatResponse {
  response: string;
}

export async function chat(query: string, sessionId?: string): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ query, session_id: sessionId }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.message || `Chat failed: ${res.status}`);
  return data.data;
}

/**
 * SSE streaming chat - calls /api/chat/stream and receives real-time events.
 * @param query - The user's query
 * @param onEvent - Callback for each SSE event
 * @param onDone - Called when stream completes
 * @param onError - Called on error
 * @returns AbortController to cancel the stream
 */
export function streamChat(
  query: string,
  onEvent: (event: { type: string; message: string }) => void,
  onDone: () => void,
  onError: (error: Error) => void,
  sessionId?: string
): AbortController {
  const controller = new AbortController();

  fetch(`${BASE}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ query, session_id: sessionId }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        throw new Error(`Stream failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from buffer
        const lines = buffer.split("\n");
        buffer = lines.pop() || ""; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);

              // Check for completion
              if (data.type === "done") {
                onDone();
                return;
              }
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }

      onDone();
    })
    .catch((error) => {
      if (error.name !== "AbortError") {
        onError(error);
      }
    });

  return controller;
}

// ============================================================================
// Settings & Connections API
// ============================================================================

function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem("auth_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface UserSettings {
  theme?: string;
  default_model?: string;
  notifications_enabled?: boolean;
}

export interface UserConnection {
  id: string;
  limb_id: string;
  is_enabled: boolean;
  last_verified_at?: string;
  created_at: string;
}

/**
 * Get user settings (preferences)
 */
export async function getUserSettings(): Promise<UserSettings | null> {
  try {
    const res = await fetch(`${BASE}/api/settings`, {
      headers: { ...getAuthHeaders() },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

/**
 * Update user settings
 */
export async function updateUserSettings(settings: UserSettings): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/api/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify(settings),
    });
    return res.ok;
  } catch {
    return false;
  }
}

/**
 * Get all user connections (limbs)
 */
export async function getUserConnections(): Promise<UserConnection[]> {
  try {
    const res = await fetch(`${BASE}/api/settings/connections`, {
      headers: { ...getAuthHeaders() },
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

/**
 * Connect a limb (save credentials)
 */
export async function connectLimb(
  limbId: string,
  credentials: Record<string, string>
): Promise<{ success: boolean; error?: string }> {
  try {
    const res = await fetch(`${BASE}/api/settings/connections/${limbId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify(credentials), // Send flat object matching backend schema (e.g. { token: "..." })
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      return { success: false, error: error.detail || "Connection failed" };
    }
    return { success: true };
  } catch (e) {
    return { success: false, error: String(e) };
  }
}

/**
 * Disconnect a limb (remove credentials)
 */
export async function disconnectLimb(
  limbId: string
): Promise<{ success: boolean; error?: string }> {
  try {
    const res = await fetch(`${BASE}/api/settings/connections/${limbId}`, {
      method: "DELETE",
      headers: { ...getAuthHeaders() },
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      return { success: false, error: error.detail || "Disconnect failed" };
    }
    return { success: true };
  } catch (e) {
    return { success: false, error: String(e) };
  }
}

/**
 * Exchange Gmail OAuth code for tokens
 */
export async function exchangeGmailToken(
  code: string,
  clientConfig: any
): Promise<{ success: boolean; message: string }> {
  try {
    const res = await fetch(`${BASE}/api/settings/connections/gmail/exchange`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify({ code, client_config: clientConfig }),
    });

    const data = await res.json();
    if (!res.ok) {
      return { success: false, message: data.detail || "Failed to connect" };
    }
    return { success: true, message: data.message };
  } catch (error) {
    return { success: false, message: "Network error" };
  }
}

/**
 * Exchange Google Calendar OAuth code for tokens
 */
export async function exchangeCalendarToken(
  code: string,
  clientConfig: any
): Promise<{ success: boolean; message: string }> {
  try {
    const res = await fetch(`${BASE}/api/settings/connections/calendar/exchange`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify({ code, client_config: clientConfig }),
    });

    const data = await res.json();
    if (!res.ok) {
      return { success: false, message: data.detail || "Failed to connect" };
    }
    return { success: true, message: data.message };
  } catch (error) {
    return { success: false, message: "Network error" };
  }
}

/**
 * Exchange Google Drive OAuth code for tokens
 */
export async function exchangeDriveToken(
  code: string,
  clientConfig: any
): Promise<{ success: boolean; message: string }> {
  try {
    const res = await fetch(`${BASE}/api/settings/connections/googledrive/exchange`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify({ code, client_config: clientConfig }),
    });

    const data = await res.json();
    if (!res.ok) {
      return { success: false, message: data.detail || "Failed to connect" };
    }
    return { success: true, message: data.message };
  } catch (error) {
    return { success: false, message: "Network error" };
  }
}
// ============================================================================
// Chat History & Contexts API
// ============================================================================

export interface ChatSession {
  id: string;
  title: string;
  context_id?: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface AgentContext {
  id: string;
  name: string;
  description?: string;
  system_prompt: string;
  is_public: boolean;
}

export async function getSessions(): Promise<ChatSession[]> {
  const res = await fetch(`${BASE}/api/history`, { headers: getAuthHeaders() });
  if (!res.ok) return [];
  const data = await res.json();
  return data.data;
}

export async function createSession(title: string): Promise<ChatSession> {
  const res = await fetch(`${BASE}/api/history`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ title }),
  });
  const data = await res.json();
  return data.data;
}

export async function deleteSession(id: string): Promise<boolean> {
  const res = await fetch(`${BASE}/api/history/${id}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  return res.ok;
}

export async function getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${BASE}/api/history/${sessionId}/messages`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) return [];
  const data = await res.json();
  return data.data;
}
