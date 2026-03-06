import React, { useEffect, useState } from 'react';
import { MessageSquare, Plus, Trash2, MoreHorizontal } from 'lucide-react';
import { getSessions, deleteSession, ChatSession } from '../lib/api';

interface ChatSidebarProps {
    currentSessionId: string | null;
    onSelectSession: (id: string) => void;
    onNewChat: () => void;
    isOpen: boolean;
    onClose: () => void;
}

export function ChatSidebar({ currentSessionId, onSelectSession, onNewChat, isOpen, onClose }: ChatSidebarProps) {
    const [sessions, setSessions] = useState<ChatSession[]>([]);
    const [loading, setLoading] = useState(true);

    const loadSessions = async () => {
        try {
            const data = await getSessions();
            setSessions(data);
        } catch (error) {
            console.error("Failed to load sessions", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (isOpen) {
            loadSessions();
        }
    }, [isOpen, currentSessionId]); // Reload when isOpen changes or currentSessionId changes (e.g. new chat created)

    const handleDelete = async (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        if (confirm("Delete this chat?")) {
            await deleteSession(id);
            loadSessions();
            if (currentSessionId === id) {
                onNewChat();
            }
        }
    };

    if (!isOpen) return null;

    return (
        <div className="flex flex-col h-full">
            <div className="p-4 border-b border-border flex justify-between items-center">
                <h2 className="font-semibold text-foreground">Chat History</h2>
            </div>

            <div className="p-3">
                <button
                    onClick={onNewChat}
                    className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground py-2 px-4 rounded-md hover:bg-primary/90 transition-colors"
                >
                    <Plus className="w-4 h-4" /> New Chat
                </button>
            </div>

            <div className="flex-1 overflow-y-auto scrollbar-thin p-2 space-y-1">
                {loading ? (
                    <div className="text-center text-muted-foreground p-4">Loading...</div>
                ) : sessions.length === 0 ? (
                    <div className="text-center text-muted-foreground p-4 text-sm">No recent chats</div>
                ) : (
                    sessions.map((session) => (
                        <div
                            key={session.id}
                            onClick={() => onSelectSession(session.id)}
                            className={`group flex items-center justify-between p-3 rounded-md cursor-pointer transition-colors ${currentSessionId === session.id
                                    ? 'bg-secondary text-foreground'
                                    : 'hover:bg-secondary/50 text-muted-foreground hover:text-foreground'
                                }`}
                        >
                            <div className="flex items-center gap-3 overflow-hidden">
                                <MessageSquare className="w-4 h-4 flex-shrink-0" />
                                <span className="truncate text-sm font-medium">
                                    {session.title || "New Chat"}
                                </span>
                            </div>
                            <button
                                onClick={(e) => handleDelete(e, session.id)}
                                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/10 hover:text-destructive rounded transition-all"
                            >
                                <Trash2 className="w-3 h-3" />
                            </button>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
}
