/**
 * Chat message bubble with inline tool result cards and document badges.
 */

import type { ChatMessage as ChatMessageType } from "../../types";
import { InlineToolResult } from "./InlineToolResult";

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessageBubble({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex mb-3 ${isUser ? "justify-end pl-8" : "justify-start pr-8"}`}
    >
      <div
        className={`
          max-w-full px-3.5 py-2.5 text-sm leading-relaxed
          shadow-sm break-words
          ${
            isUser
              ? "bg-accent text-bg-primary rounded-[14px_14px_4px_14px]"
              : "bg-bg-surface text-text-primary border border-border rounded-[14px_14px_14px_4px]"
          }
        `}
      >
        {/* Text content with simple formatting */}
        {message.content && (
          <div className="whitespace-pre-wrap">{formatText(message.content)}</div>
        )}

        {/* Document attachments (user messages) */}
        {message.documents && message.documents.length > 0 && (
          <div className={`flex flex-wrap gap-1 ${message.content ? "mt-1.5" : ""}`}>
            {message.documents.map((doc) => (
              <span
                key={doc.docId}
                className={`
                  inline-flex items-center gap-1 px-2 py-0.5
                  rounded-[10px] text-[0.7rem] font-semibold
                  ${isUser ? "bg-white/20" : "bg-accent-muted text-accent"}
                `}
              >
                📄 {doc.filename}
                <span className="opacity-70">
                  ({Math.round(doc.size / 1024)} KB)
                </span>
              </span>
            ))}
          </div>
        )}

        {/* Inline tool result cards */}
        {message.toolResults?.map((tr, i) => (
          <InlineToolResult key={i} tool={tr.tool} result={tr.result} />
        ))}

        {/* Streaming indicator */}
        {message.isStreaming && !message.content && <StreamingDots />}
      </div>
    </div>
  );
}

/**
 * Simple text formatting: bold (**text**) and italic (*text*)
 */
function formatText(text: string): React.ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function StreamingDots() {
  return (
    <span className="inline-flex gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-text-tertiary"
          style={{
            animation: `pulse-dot 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
    </span>
  );
}
