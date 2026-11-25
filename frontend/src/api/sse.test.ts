import { describe, expect, it } from "vitest";
import { SseParser, SseProtocolError, type SseEvent } from "./sse";

const encoder = new TextEncoder();

// Representative frames, as backend/app/services/agent.py emits them, with
// multi-byte UTF-8 (accented letters, the euro sign and an emoji).
const FRAMES = [
  'event: text_delta\ndata: {"text": "Ciao! La zona è semicentrale, prezzo €/m² "}\n\n',
  'event: tool_result\ndata: {"tool": "valuate_property", "result": {"estimate": {"min": 304000, "max": 416000}, "nota": "Più ✓ 🏠"}}\n\n',
  'event: text_delta\ndata: {"text": "…fine"}\n\n',
  'event: error\ndata: {"error": "daily_limit", "message": "Riprova domani."}\n\n',
  "event: done\ndata: {}\n\n",
];
const STREAM = encoder.encode(FRAMES.join(""));

function parse(chunks: Uint8Array[]): SseEvent[] {
  const events: SseEvent[] = [];
  const parser = new SseParser((e) => events.push(e));
  for (const chunk of chunks) parser.push(chunk);
  parser.end();
  return events;
}

const EXPECTED = parse([STREAM]);

describe("SseParser", () => {
  it("parses the representative frames in order", () => {
    expect(EXPECTED.map((e) => e.type)).toEqual(["text_delta", "tool_result", "text_delta", "error", "done"]);
    expect(EXPECTED[0].data.text).toBe("Ciao! La zona è semicentrale, prezzo €/m² ");
    expect((EXPECTED[1].data.result as { nota: string }).nota).toBe("Più ✓ 🏠");
  });

  it("yields the same events for every two-part split of the bytes", () => {
    for (let cut = 0; cut <= STREAM.length; cut++) {
      expect(parse([STREAM.slice(0, cut), STREAM.slice(cut)])).toEqual(EXPECTED);
    }
  });

  it("yields the same events when fed one byte at a time", () => {
    const bytes = Array.from(STREAM, (b) => new Uint8Array([b]));
    expect(parse(bytes)).toEqual(EXPECTED);
  });

  it("accepts CRLF and CR line endings, split anywhere", () => {
    for (const ending of ["\r\n", "\r"]) {
      const stream = encoder.encode(FRAMES.join("").split("\n").join(ending));
      for (let cut = 0; cut <= stream.length; cut++) {
        expect(parse([stream.slice(0, cut), stream.slice(cut)])).toEqual(EXPECTED);
      }
    }
  });

  it("joins multi-line data and skips comments", () => {
    const stream = encoder.encode(': keep-alive\nevent: text_delta\ndata: {"text":\ndata:  "riga"}\n\n');
    expect(parse([stream])).toEqual([{ type: "text_delta", data: { text: "riga" } }]);
  });

  it("reports a stream that ends inside an event", () => {
    const partial = encoder.encode('event: text_delta\ndata: {"text": "a"}\n');
    expect(() => parse([partial])).toThrow(SseProtocolError);
  });

  it("reports malformed JSON instead of dropping it", () => {
    expect(() => parse([encoder.encode("event: text_delta\ndata: {not json}\n\n")])).toThrow(SseProtocolError);
  });

  it("lets an error thrown by the callback propagate", () => {
    const parser = new SseParser(() => {
      throw new Error("callback failed");
    });
    expect(() => parser.push(encoder.encode("event: done\ndata: {}\n\n"))).toThrow("callback failed");
  });
});
