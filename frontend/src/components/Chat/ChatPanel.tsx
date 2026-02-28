/**
 * Main chat panel: message list + input bar.
 * Fills the sidebar and streams responses from the AI agent.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatMessage, ChatToolResult, Coordinates } from "../../types";
import { streamChat, type StreamChatEvent } from "../../api/client";
import { ChatMessageBubble } from "./ChatMessage";

interface ChatPanelProps {
  onMapUpdate: (coords: Coordinates) => void;
}

let messageIdCounter = 0;
function nextId(): string {
  return `msg-${++messageIdCounter}`;
}

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Ciao! Sono il tuo consulente di valutazione immobiliare. " +
    "Dimmi l'indirizzo dell'immobile che vuoi valutare e la superficie in m2, " +
    "e ti daro una stima basata sui dati ufficiali OMI.\n\n" +
    "Posso anche spiegarti come funzionano le valutazioni delle agenzie e " +
    "perche a volte sottovalutano gli immobili. 🏠",
};

export function ChatPanel({ onMapUpdate }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if (!trimmed || isStreaming) return;

    // Add user message
    const userMsg: ChatMessage = {
      id: nextId(),
      role: "user",
      content: trimmed,
    };

    // Create placeholder for assistant response
    const assistantId = nextId();
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      toolResults: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setIsStreaming(true);

    // Build conversation history for API (exclude welcome message and streaming state)
    const history = [...messages.filter((m) => m.id !== "welcome"), userMsg].map(
      (m) => ({
        role: m.role,
        content: m.content,
      })
    );

    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      await streamChat(
        history,
        (event: StreamChatEvent) => {
          if (event.type === "text_delta") {
            const text = (event.data as { text: string }).text;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + text }
                  : m
              )
            );
          } else if (event.type === "tool_result") {
            const toolResult: ChatToolResult = {
              tool: (event.data as { tool: string }).tool,
              result: (event.data as { result: Record<string, unknown> }).result,
            };
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, toolResults: [...(m.toolResults || []), toolResult] }
                  : m
              )
            );
          } else if (event.type === "map_update") {
            const coords = event.data as unknown as Coordinates;
            onMapUpdate(coords);
          } else if (event.type === "error") {
            const errorMsg = (event.data as { message: string }).message;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, content: m.content + `\n\n⚠️ Errore: ${errorMsg}`, isStreaming: false }
                  : m
              )
            );
          } else if (event.type === "done") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, isStreaming: false } : m
              )
            );
          }
        },
        abortController.signal
      );
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content:
                    m.content +
                    `\n\n⚠️ Errore di connessione: ${(err as Error).message}`,
                  isStreaming: false,
                }
              : m
          )
        );
      }
    } finally {
      setIsStreaming(false);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, isStreaming: false } : m
        )
      );
      abortControllerRef.current = null;
    }
  }, [input, isStreaming, messages, onMapUpdate]);

  const handleStop = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div style={styles.container}>
      {/* Messages area */}
      <div style={styles.messages}>
        {messages.map((msg) => (
          <ChatMessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div style={styles.inputBar}>
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Scrivi un indirizzo da valutare..."
          style={styles.textarea}
          rows={1}
          disabled={isStreaming}
        />
        {isStreaming ? (
          <button onClick={handleStop} style={styles.stopButton} title="Ferma">
            ■
          </button>
        ) : (
          <button
            onClick={handleSend}
            style={{
              ...styles.sendButton,
              opacity: input.trim() ? 1 : 0.4,
            }}
            disabled={!input.trim()}
            title="Invia"
          >
            ↑
          </button>
        )}
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    flexDirection: "column" as const,
    height: "100%",
    overflow: "hidden",
  } as React.CSSProperties,
  messages: {
    flex: 1,
    overflowY: "auto" as const,
    padding: "16px 12px",
    display: "flex",
    flexDirection: "column" as const,
  } as React.CSSProperties,
  inputBar: {
    display: "flex",
    gap: "8px",
    padding: "12px",
    borderTop: "1px solid #e2e8f0",
    backgroundColor: "#fff",
    alignItems: "flex-end",
  } as React.CSSProperties,
  textarea: {
    flex: 1,
    resize: "none" as const,
    border: "1px solid #e2e8f0",
    borderRadius: "12px",
    padding: "10px 14px",
    fontSize: "0.85rem",
    lineHeight: 1.5,
    fontFamily: "inherit",
    outline: "none",
    maxHeight: "120px",
    minHeight: "40px",
  } as React.CSSProperties,
  sendButton: {
    width: "36px",
    height: "36px",
    borderRadius: "50%",
    border: "none",
    backgroundColor: "#2b6cb0",
    color: "#fff",
    fontSize: "1.1rem",
    fontWeight: 700,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  } as React.CSSProperties,
  stopButton: {
    width: "36px",
    height: "36px",
    borderRadius: "50%",
    border: "none",
    backgroundColor: "#e53e3e",
    color: "#fff",
    fontSize: "0.9rem",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  } as React.CSSProperties,
};
