import { useState, useCallback, useRef } from 'react';
import { useAuth } from '@/context/AuthContext';
import { BASE } from '@/lib/api';

export interface StreamLog {
    id: string;
    type: 'info' | 'action' | 'result' | 'error' | 'response' | 'done';
    message: string;
    timestamp: number;
}

interface UseAgentStreamReturn {
    logs: StreamLog[];
    isStreaming: boolean;
    error: string | null;
    streamAgent: (query: string, options?: {
        onLog?: (log: StreamLog) => void;
        onDone?: (finalResponse: string) => void;
        onError?: (error: string) => void;
        sessionId?: string;
    }) => Promise<string | null>;
    clearLogs: () => void;
}

export function useAgentStream(): UseAgentStreamReturn {
    const [logs, setLogs] = useState<StreamLog[]>([]);
    const [isStreaming, setIsStreaming] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const { token } = useAuth(); // Get auth token

    const clearLogs = useCallback(() => {
        setLogs([]);
        setError(null);
    }, []);

    const streamAgent = useCallback(async (
        query: string,
        options?: {
            onLog?: (log: StreamLog) => void;
            onDone?: (finalResponse: string) => void;
            onError?: (error: string) => void;
            sessionId?: string;
        }
    ): Promise<string | null> => {
        setIsStreaming(true);
        setError(null);
        setLogs([]);

        // Abort previous request
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }
        abortControllerRef.current = new AbortController();

        let finalResponse: string | null = null;
        let accumulatedResponse = "";

        try {
            const headers: Record<string, string> = {
                "Content-Type": "application/json",
            };

            if (token) {
                headers["Authorization"] = `Bearer ${token}`;
            }

            const body = {
                query,
                session_id: options?.sessionId
            };

            const response = await fetch(`${BASE}/api/chat/stream`, {
                method: 'POST',
                headers,
                body: JSON.stringify(body),
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            if (!response.body) {
                throw new Error('Response body is null');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');

                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.trim() === '') continue;

                    if (line.startsWith('data: ')) {
                        const dataStr = line.slice(6);
                        if (dataStr === '[DONE]') continue;

                        try {
                            const event = JSON.parse(dataStr);

                            const newLog: StreamLog = {
                                id: crypto.randomUUID(),
                                type: event.type,
                                message: event.message,
                                timestamp: Date.now(),
                            };

                            setLogs(prev => [...prev, newLog]);

                            if (options?.onLog) {
                                options.onLog(newLog);
                            }

                            if (event.type === 'response') {
                                finalResponse = event.message;
                                accumulatedResponse = event.message;
                            } else if (event.type === 'error') {
                                console.error("Agent stream error:", event.message);
                                if (options?.onError) options.onError(event.message);
                            }

                        } catch (e) {
                            console.warn('Failed to parse SSE event:', dataStr, e);
                        }
                    }
                }
            }

            if (options?.onDone) {
                options.onDone(finalResponse || "Request complete");
            }

        } catch (err: any) {
            if (err.name === 'AbortError') {
                console.log('Stream aborted');
            } else {
                console.error('Stream error:', err);
                const errMsg = err.message || 'Failed to connect to agent stream';
                setError(errMsg);

                const errorLog: StreamLog = {
                    id: crypto.randomUUID(),
                    type: 'error',
                    message: `Connection failed: ${errMsg}`,
                    timestamp: Date.now()
                };
                setLogs(prev => [...prev, errorLog]);

                if (options?.onError) options.onError(errMsg);
                if (options?.onLog) options.onLog(errorLog);
            }
        } finally {
            setIsStreaming(false);
            abortControllerRef.current = null;
        }

        return finalResponse;
    }, [token]);

    return { logs, isStreaming, error, streamAgent, clearLogs };
}
