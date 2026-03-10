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

    const userMsg: ChatMessage = {
      id: nextId(),
      role: "user",
      content: trimmed || (pendingDocs.length > 0 ? "Analizza questi documenti." : ""),
      documents: pendingDocs.length > 0 ? [...pendingDocs] : undefined,
    };

    const currentDocs = [...pendingDocs];
    setPendingDocs([]);

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
  const isAttachDisabled = isStreaming || isUploading || pendingDocs.length >= MAX_FILES;

  return (
    <div className="flex flex-col h-full overflow-hidden bg-bg-elevated">
      {/* Messages area with drag-and-drop */}
      <div
        className={`
          flex-1 overflow-y-auto p-4 flex flex-col relative
          ${isDragOver ? "bg-accent-muted/30" : ""}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {isDragOver && (
          <div className="absolute inset-2 flex items-center justify-center bg-accent-muted/20 border-2 border-dashed border-accent rounded-xl text-sm text-accent font-semibold z-10 pointer-events-none">
            Trascina qui i tuoi PDF
          </div>
        )}
        {messages.map((msg) => (
          <ChatMessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input bar */}
      <div className="flex gap-2 p-3 border-t border-border bg-bg-primary items-end">
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          multiple
          className="hidden"
          onChange={(e) => handleFileSelect(e.target.files)}
        />

        {/* Paperclip upload button */}
        <button
          onClick={() => fileInputRef.current?.click()}
          className={`
            w-9 h-9 rounded-full border border-border bg-bg-surface
            text-lg flex items-center justify-center shrink-0
            hover:border-border-light hover:bg-bg-elevated
            transition-colors cursor-pointer
            ${isAttachDisabled ? "opacity-40 cursor-not-allowed" : ""}
          `}
          disabled={isAttachDisabled}
          title="Allega PDF"
        >
          {isUploading ? "..." : "\uD83D\uDCCE"}
        </button>

        {/* Textarea + pending docs */}
        <div className="flex-1 flex flex-col">
          {/* Pending document chips */}
          {pendingDocs.length > 0 && (
            <div className="flex flex-wrap gap-1 pb-1.5">
              {pendingDocs.map((doc) => (
                <span
                  key={doc.docId}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-accent-muted text-accent text-xs font-semibold border border-accent/30"
                >
                  📄 {doc.filename}
                  <button
                    onClick={() =>
                      setPendingDocs((prev) =>
                        prev.filter((d) => d.docId !== doc.docId)
                      )
                    }
                    className="text-text-tertiary hover:text-text-secondary text-[0.65rem] px-0.5 cursor-pointer bg-transparent border-none"
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
            className="
              flex-1 resize-none border border-border rounded-xl
              px-3.5 py-2.5 text-sm leading-relaxed
              font-[inherit] outline-none
              max-h-[120px] min-h-[40px]
              bg-bg-surface text-text-primary
              placeholder:text-text-tertiary
              focus:border-accent/50 focus:ring-1 focus:ring-accent/20
              transition-colors
            "
            rows={1}
            disabled={isStreaming}
          />
        </div>

        {/* Send / Stop button */}
        {isStreaming ? (
          <button
            onClick={handleStop}
            className="w-9 h-9 rounded-full bg-danger text-white text-sm flex items-center justify-center shrink-0 cursor-pointer border-none hover:bg-danger/80 transition-colors"
            title="Ferma"
          >
            ■
          </button>
        ) : (
          <button
            onClick={handleSend}
            className={`
              w-9 h-9 rounded-full bg-accent text-bg-primary
              text-lg font-bold flex items-center justify-center shrink-0
              cursor-pointer border-none
              hover:bg-accent-hover transition-colors
              ${canSend ? "opacity-100" : "opacity-40 cursor-not-allowed"}
            `}
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
