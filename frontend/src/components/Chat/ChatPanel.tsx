/**
 * Main chat panel: message list + input bar with PDF upload.
 * Fills the sidebar and streams responses from the AI agent.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ChatMessage,
  ChatToolResult,
  Coordinates,
  UploadedDocument,
} from "../../types";
import {
  streamChat,
  uploadDocument,
  type StreamChatEvent,
} from "../../api/client";
import { ChatMessageBubble } from "./ChatMessage";

interface ChatPanelProps {
  onMapUpdate: (coords: Coordinates) => void;
}

let messageIdCounter = 0;
function nextId(): string {
  return `msg-${++messageIdCounter}`;
}

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5 MB
const MAX_FILES = 4;

const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "Ciao! Sono il tuo consulente di valutazione immobiliare. " +
    "Lavoro per te, non per un'agenzia.\n\n" +
    "Dimmi l'indirizzo dell'immobile che vuoi valutare e ti guido " +
    "passo passo nella stima, basata sui dati ufficiali OMI.\n\n" +
    "Se hai documenti catastali (visure, planimetrie), puoi allegarli " +
    "con la graffetta.",
};

export function ChatPanel({ onMapUpdate }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [pendingDocs, setPendingDocs] = useState<UploadedDocument[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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

  // --- File upload handling ---

  const handleFileSelect = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return;

      if (pendingDocs.length + files.length > MAX_FILES) {
        alert(`Massimo ${MAX_FILES} documenti per messaggio.`);
        return;
      }

      setIsUploading(true);
      try {
        for (const file of Array.from(files)) {
          if (file.type !== "application/pdf") {
            alert(`"${file.name}" non e un PDF. Solo file PDF sono supportati.`);
            continue;
          }
          if (file.size > MAX_FILE_SIZE) {
            alert(`"${file.name}" supera il limite di 5 MB.`);
            continue;
          }
          const doc = await uploadDocument(file);
          setPendingDocs((prev) => [...prev, doc]);
        }
      } catch (err) {
        alert(`Errore durante il caricamento: ${(err as Error).message}`);
      } finally {
        setIsUploading(false);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }
    },
    [pendingDocs]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      handleFileSelect(e.dataTransfer.files);
    },
    [handleFileSelect]
  );

  // --- Send message ---

  const handleSend = useCallback(async () => {
    const trimmed = input.trim();
    if ((!trimmed && pendingDocs.length === 0) || isStreaming) return;

    // Add user message (with optional documents)
    const userMsg: ChatMessage = {
      id: nextId(),
      role: "user",
      content: trimmed || (pendingDocs.length > 0 ? "Analizza questi documenti." : ""),
      documents: pendingDocs.length > 0 ? [...pendingDocs] : undefined,
    };

    // Clear pending docs
    const currentDocs = [...pendingDocs];
    setPendingDocs([]);

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

    // Build conversation history for API (exclude welcome message)
    // Only include document_ids for the LAST user message (avoids TTL expiration on replay)
    const allMsgs = [...messages.filter((m) => m.id !== "welcome"), userMsg];
    const history = allMsgs.map((m, idx) => ({
      role: m.role,
      content: m.content,
      ...(m.documents?.length && idx === allMsgs.length - 1
        ? { document_ids: m.documents.map((d) => d.docId) }
        : {}),
    }));

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
        // If document expired, mention it
        const errMsg = (err as Error).message;
        const isDocExpired = errMsg.includes("scaduto");
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? {
                  ...m,
                  content:
                    m.content +
                    `\n\n⚠️ ${isDocExpired ? "Documento scaduto. Ricaricalo e riprova." : `Errore di connessione: ${errMsg}`}`,
                  isStreaming: false,
                }
              : m
          )
        );
        // If docs expired, restore them so user can retry
        if (isDocExpired && currentDocs.length > 0) {
          setPendingDocs(currentDocs);
        }
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
  }, [input, isStreaming, messages, onMapUpdate, pendingDocs]);

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

  const canSend = input.trim() || pendingDocs.length > 0;

  return (
    <div style={styles.container}>
      {/* Messages area with drag-and-drop */}
      <div
        style={{
          ...styles.messages,
          ...(isDragOver ? styles.messagesDragOver : {}),
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {isDragOver && (
          <div style={styles.dropOverlay}>Trascina qui i tuoi PDF</div>
        )}
        {messages.map((msg) => (
          <ChatMessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div style={styles.inputBar}>
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          multiple
          style={{ display: "none" }}
          onChange={(e) => handleFileSelect(e.target.files)}
        />

        {/* Paperclip upload button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          style={{
            ...styles.attachButton,
            opacity: isStreaming || isUploading || pendingDocs.length >= MAX_FILES ? 0.4 : 1,
          }}
          disabled={isStreaming || isUploading || pendingDocs.length >= MAX_FILES}
          title="Allega PDF"
        >
          {isUploading ? "..." : "\uD83D\uDCCE"}
        </button>

        {/* Textarea + pending docs */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column" as const }}>
          {/* Pending document chips */}
          {pendingDocs.length > 0 && (
            <div style={styles.pendingDocsRow}>
              {pendingDocs.map((doc) => (
                <span key={doc.docId} style={styles.docChip}>
                  📄 {doc.filename}
                  <button
                    onClick={() =>
                      setPendingDocs((prev) =>
                        prev.filter((d) => d.docId !== doc.docId)
                      )
                    }
                    style={styles.removeChip}
                    title="Rimuovi"
                  >
                    ✕
                  </button>
                </span>
              ))}
            </div>
          )}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              pendingDocs.length > 0
                ? "Scrivi un messaggio o premi Invio per analizzare..."
                : "Scrivi un indirizzo da valutare..."
            }
            style={styles.textarea}
            rows={1}
            disabled={isStreaming}
          />
        </div>

        {/* Send / Stop button */}
        {isStreaming ? (
          <button onClick={handleStop} style={styles.stopButton} title="Ferma">
            ■
          </button>
        ) : (
          <button
            onClick={handleSend}
            style={{
              ...styles.sendButton,
              opacity: canSend ? 1 : 0.4,
            }}
            disabled={!canSend}
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
    position: "relative" as const,
  } as React.CSSProperties,
  messagesDragOver: {
    backgroundColor: "#ebf8ff",
  } as React.CSSProperties,
  dropOverlay: {
    position: "absolute" as const,
    inset: "8px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "rgba(43, 108, 176, 0.08)",
    border: "2px dashed #2b6cb0",
    borderRadius: "8px",
    fontSize: "0.9rem",
    color: "#2b6cb0",
    fontWeight: 600,
    zIndex: 10,
    pointerEvents: "none" as const,
  } as React.CSSProperties,
  inputBar: {
    display: "flex",
    gap: "8px",
    padding: "12px",
    borderTop: "1px solid #e2e8f0",
    backgroundColor: "#fff",
    alignItems: "flex-end",
  } as React.CSSProperties,
  attachButton: {
    width: "36px",
    height: "36px",
    borderRadius: "50%",
    border: "1px solid #e2e8f0",
    backgroundColor: "#fff",
    fontSize: "1.1rem",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
  } as React.CSSProperties,
  pendingDocsRow: {
    display: "flex",
    flexWrap: "wrap" as const,
    gap: "4px",
    padding: "4px 0 6px 0",
  } as React.CSSProperties,
  docChip: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    padding: "2px 8px",
    borderRadius: "12px",
    backgroundColor: "#ebf8ff",
    color: "#2b6cb0",
    fontSize: "0.72rem",
    fontWeight: 600,
    border: "1px solid #bee3f8",
  } as React.CSSProperties,
  removeChip: {
    background: "none",
    border: "none",
    color: "#a0aec0",
    cursor: "pointer",
    fontSize: "0.7rem",
    padding: "0 2px",
    lineHeight: 1,
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
