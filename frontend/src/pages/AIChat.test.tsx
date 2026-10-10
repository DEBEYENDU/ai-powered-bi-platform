import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { StrictMode } from "react";
import { AIChat } from "./AIChat";
import { AppTheme, useColorMode } from "../theme";
import { fetchWithAuth } from "../api";

// jsdom has no layout engine: scrolling is a no-op there.
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

const conversation = {
  id: "c1",
  title: "Quarterly review",
  model: "meta/llama-3.2-11b-vision-instruct",
  provider: "openai",
  message_count: 2,
  total_tokens: 0,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const messages = [
  {
    id: "m1",
    role: "user",
    content: "What is a dashboard?",
    token_count: 5,
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "m2",
    role: "assistant",
    content: "A dashboard is a **visual summary** of key metrics.",
    token_count: 9,
    created_at: "2026-01-01T00:00:01Z",
  },
];

vi.mock("../api", () => ({
  rget: vi.fn(async (url: string) => {
    if (url === "/ai/conversations") return { data: [conversation] };
    if (url.startsWith("/ai/conversations/")) return { messages };
    if (url === "/ai/providers") {
      return [
        {
          id: "openai",
          name: "OpenAI",
          models: ["meta/llama-3.2-11b-vision-instruct"],
          available: true,
          configured: true,
          default_model: "meta/llama-3.2-11b-vision-instruct",
        },
      ];
    }
    throw new Error(`unexpected url: ${url}`);
  }),
  rpost: vi.fn(async () => conversation),
  fetchWithAuth: vi.fn(async () => ({ ok: true, status: 200, statusText: "OK" })),
}));

function ColorModeToggle() {
  const { toggle } = useColorMode();
  return (
    <button type="button" onClick={toggle}>
      switch-mode
    </button>
  );
}

async function renderChat() {
  render(
    <AppTheme>
      <ColorModeToggle />
      <AIChat />
    </AppTheme>
  );
  await waitFor(() => expect(screen.getByText("Quarterly review")).toBeInTheDocument());
  fireEvent.click(screen.getByText("Quarterly review"));
  await waitFor(() =>
    expect(screen.getByText(/A dashboard is a/)).toBeInTheDocument()
  );
}

function bubbleOf(node: HTMLElement): HTMLElement {
  const bubble = node.closest(".MuiPaper-root");
  if (!bubble) throw new Error("no bubble ancestor");
  return bubble as HTMLElement;
}

/** jsdom resolves emotion rules through getComputedStyle; fall back to raw CSS. */
function styleOf(el: HTMLElement, property: string): string {
  const computed = getComputedStyle(el).getPropertyValue(property);
  if (computed && computed !== "rgba(0, 0, 0, 0)" && computed !== "transparent") return computed;
  const css = Array.from(document.querySelectorAll("style"))
    .map((s) => s.textContent || "")
    .join("\n");
  const match = css.match(new RegExp(`${property}\\s*:\\s*([^;{}]+)`, "g"));
  return match ? match[match.length - 1].split(":")[1].trim() : "";
}

describe("AI chat light/dark mode contrast", () => {
  it("renders the assistant bubble readable in light mode", async () => {
    await renderChat();
    const bubble = bubbleOf(screen.getByText(/A dashboard is a/));
    const bg = styleOf(bubble, "background-color");
    const color = styleOf(bubble, "color");
    expect(bg).toMatch(/250, 250, 250|#fafafa/i);
    expect(color).toMatch(/0, 0, 0|#000/i);
  });

  it("renders the user bubble as white text", async () => {
    await renderChat();
    const bubble = bubbleOf(screen.getByText("What is a dashboard?"));
    expect(styleOf(bubble, "color")).toMatch(/255, 255, 255|#fff/i);
  });

  it("keeps the assistant bubble readable after switching to dark mode", async () => {
    await renderChat();
    fireEvent.click(screen.getByText("switch-mode"));
    await waitFor(() => {
      expect(getComputedStyle(document.body).color).toBeTruthy();
    });
    const bubble = bubbleOf(screen.getByText(/A dashboard is a/));
    expect(styleOf(bubble, "background-color")).toMatch(/33, 33, 33|#212121/i);
    expect(styleOf(bubble, "color")).toMatch(/255, 255, 255|#fff/i);
  });
});

/* ------------------------------------------------------------------ */
/*  Streaming: exactly-once rendering under StrictMode                 */
/* ------------------------------------------------------------------ */

/** Minimal SSE response: body.getReader() yields the given chunks once. */
function sseStreamResponse(events: string[]) {
  const encoder = new TextEncoder();
  let i = 0;
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    body: {
      getReader: () => ({
        read: () =>
          i < events.length
            ? Promise.resolve({ done: false, value: encoder.encode(events[i++]) })
            : Promise.resolve({ done: true, value: undefined as unknown as Uint8Array }),
      }),
    },
  };
}

function sseEvents(deltas: string[]): string[] {
  return [
    ...deltas.map(
      (d) =>
        `data: ${JSON.stringify({ delta: d, conversation_id: "c1", finish_reason: null })}\n\n`
    ),
    `data: ${JSON.stringify({
      delta: "",
      conversation_id: "c1",
      finish_reason: "stop",
      usage: { message_id: "m9", total_tokens: 12 },
    })}\n\n`,
    "data: [DONE]\n\n",
  ];
}

describe("AI chat streaming under StrictMode", () => {
  it("renders each streamed delta exactly once — no doubled words", async () => {
    // "data data" is a LEGITIMATE repetition: the renderer must preserve it
    // verbatim (no word-dedup filter), while still not doubling each chunk.
    vi.mocked(fetchWithAuth).mockImplementationOnce(async () =>
      sseStreamResponse(
        sseEvents(["Business", " Intelligence", " Support", " for ", "data data ", "review."])
      ) as unknown as Response
    );
    render(
      <StrictMode>
        <AppTheme>
          <AIChat />
        </AppTheme>
      </StrictMode>
    );
    await waitFor(() => expect(screen.getByText("Quarterly review")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Quarterly review"));
    await waitFor(() => expect(screen.getByText(/A dashboard is a/)).toBeInTheDocument());

    const input = screen.getByPlaceholderText(/Type your message/);
    fireEvent.change(input, { target: { value: "What is revenue?" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() =>
      expect(
        screen.getByText("Business Intelligence Support for data data review.")
      ).toBeInTheDocument()
    );
    expect(screen.queryByText(/BusinessBusiness/)).toBeNull();
    expect(screen.queryByText(/data data data/)).toBeNull();
  });
});
