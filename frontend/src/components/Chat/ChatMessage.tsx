/**
 * Chat message bubble with inline tool result cards.
 */

import type { ChatMessage as ChatMessageType } from "../../types";
import { InlineToolResult } from "./InlineToolResult";

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessageBubble({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div style={{
      display: "flex",
      justifyContent: isUser ? "flex-end" : "flex-start",
      marginBottom: "12px",
      paddingLeft: isUser ? "32px" : "0",
      paddingRight: isUser ? "0" : "32px",
    }}>
      <div style={{
        maxWidth: "100%",
        padding: "10px 14px",
        borderRadius: isUser ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
        backgroundColor: isUser ? "#2b6cb0" : "#fff",
        color: isUser ? "#fff" : "#2d3748",
        border: isUser ? "none" : "1px solid #e2e8f0",
        fontSize: "0.85rem",
        lineHeight: 1.6,
        boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
        wordBreak: "break-word" as const,
      }}>
        {/* Text content with simple formatting */}
        {message.content && (
          <div style={{ whiteSpace: "pre-wrap" }}>
            {formatText(message.content)}
          </div>
        )}

        {/* Inline tool result cards */}
        {message.toolResults?.map((tr, i) => (
          <InlineToolResult key={i} tool={tr.tool} result={tr.result} />
        ))}

        {/* Streaming indicator */}
        {message.isStreaming && !message.content && (
          <StreamingDots />
        )}
      </div>
    </div>
  );
}

/**
 * Simple text formatting: bold (**text**) and italic (*text*)
 */
function formatText(text: string): React.ReactNode {
  // Split by bold markers first
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
    <span style={{
      display: "inline-flex",
      gap: "3px",
      padding: "4px 0",
    }}>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            backgroundColor: "#a0aec0",
            animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
      <style>{`
        @keyframes pulse {
          0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </span>
  );
}
