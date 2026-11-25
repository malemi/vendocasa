/**
 * Server-Sent Events parser for the chat stream.
 *
 * Network reads split the stream at arbitrary byte positions, including inside
 * a UTF-8 character, a line or an event. The parser keeps its decoder, line
 * buffer and pending event across reads, so the events it emits do not depend
 * on where the splits fall. It accepts LF, CRLF and CR line endings, multi-line
 * `data:` fields and `:` comment lines.
 *
 * A malformed JSON payload, or a stream that ends in the middle of an event, is
 * reported as an SseProtocolError rather than dropped. Errors thrown by the
 * event callback propagate to the caller unchanged.
 */

export interface SseEvent {
  type: string;
  data: Record<string, unknown>;
}

export class SseProtocolError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SseProtocolError";
  }
}

export class SseParser {
  private readonly decoder = new TextDecoder();
  private buffer = "";
  private eventType = "";
  private dataLines: string[] = [];
  private sawField = false;
  private pendingCR = false;

  constructor(private readonly onEvent: (event: SseEvent) => void) {}

  /** Feed the next bytes read from the stream. */
  push(bytes: Uint8Array): void {
    this.consume(this.decoder.decode(bytes, { stream: true }));
  }

  /** The stream has ended: flush the decoder and check nothing is left half-read. */
  end(): void {
    this.consume(this.decoder.decode());
    if (this.buffer !== "") {
      this.line(this.buffer);
      this.buffer = "";
    }
    if (this.sawField) {
      throw new SseProtocolError("stream ended in the middle of an event");
    }
  }

  private consume(text: string): void {
    for (const char of text) {
      if (this.pendingCR) {
        this.pendingCR = false;
        if (char === "\n") continue; // CRLF: the CR already ended the line
      }
      if (char === "\r") {
        this.pendingCR = true;
        this.line(this.buffer);
        this.buffer = "";
      } else if (char === "\n") {
        this.line(this.buffer);
        this.buffer = "";
      } else {
        this.buffer += char;
      }
    }
  }

  private line(line: string): void {
    if (line === "") {
      this.dispatch();
      return;
    }
    if (line.startsWith(":")) return; // comment
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);
    if (field === "event") {
      this.eventType = value;
      this.sawField = true;
    } else if (field === "data") {
      this.dataLines.push(value);
      this.sawField = true;
    }
    // Other fields (id, retry) are not used by this stream.
  }

  private dispatch(): void {
    const type = this.eventType;
    const lines = this.dataLines;
    this.eventType = "";
    this.dataLines = [];
    this.sawField = false;
    if (lines.length === 0) return;
    let data: unknown;
    try {
      data = JSON.parse(lines.join("\n"));
    } catch {
      throw new SseProtocolError(`malformed JSON in a "${type || "message"}" event`);
    }
    if (typeof data !== "object" || data === null || Array.isArray(data)) {
      throw new SseProtocolError(`non-object data in a "${type || "message"}" event`);
    }
    this.onEvent({ type: type || "message", data: data as Record<string, unknown> });
  }
}
