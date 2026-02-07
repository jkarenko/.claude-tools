/**
 * POF Dashboard Server
 *
 * Real-time monitoring for POF agent workflow.
 * Zero dependencies — runs on Bun's built-in HTTP server.
 *
 * Start:  bun run dashboard/server.ts
 * View:   http://localhost:3456
 * Stop:   Ctrl+C or POST /api/shutdown
 */

const PORT = parseInt(process.env.POF_DASHBOARD_PORT || "3456");

// --- Types ---

interface StatusUpdate {
  agent: string;
  phase?: string;
  status?: "started" | "working" | "complete" | "error" | "blocked";
  message: string;
  detail?: string;
  timestamp?: string;
}

interface Question {
  id: string;
  agent: string;
  question: string;
  options?: string[];
  timestamp: string;
  answered: boolean;
  answer?: string;
  answeredAt?: string;
}

// --- State (in-memory, ephemeral) ---

const state = {
  agents: new Map<string, StatusUpdate & { lastSeen: string }>(),
  questions: [] as Question[],
  log: [] as (StatusUpdate & { timestamp: string })[],
  startedAt: new Date().toISOString(),
};

// --- SSE Client Management ---

const sseClients = new Set<ReadableStreamDefaultController>();
const encoder = new TextEncoder();

function broadcast(event: string, data: unknown) {
  const payload = encoder.encode(
    `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
  );
  for (const client of sseClients) {
    try {
      client.enqueue(payload);
    } catch {
      sseClients.delete(client);
    }
  }
}

// --- Helpers ---

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });

async function parseBody<T>(req: Request): Promise<T | null> {
  try {
    return (await req.json()) as T;
  } catch {
    return null;
  }
}

// --- Server ---

const htmlPath = import.meta.dir + "/index.html";

const server = Bun.serve({
  port: PORT,

  fetch: async (req) => {
    const url = new URL(req.url);
    const { pathname } = url;
    const method = req.method;

    // --- Serve UI ---

    if (pathname === "/" || pathname === "/index.html") {
      return new Response(Bun.file(htmlPath));
    }

    // --- Health check ---

    if (pathname === "/health") {
      const uptime = (Date.now() - new Date(state.startedAt).getTime()) / 1000;
      return json({ ok: true, uptime: Math.round(uptime), clients: sseClients.size });
    }

    // --- SSE event stream ---

    if (pathname === "/api/events") {
      const stream = new ReadableStream({
        start(controller) {
          sseClients.add(controller);

          const init = encoder.encode(
            `event: init\ndata: ${JSON.stringify({
              agents: Object.fromEntries(state.agents),
              questions: state.questions,
              log: state.log.slice(-100),
              startedAt: state.startedAt,
            })}\n\n`
          );
          controller.enqueue(init);

          req.signal.addEventListener("abort", () => {
            sseClients.delete(controller);
          });
        },
      });

      return new Response(stream, {
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
        },
      });
    }

    // --- Agent status report ---

    if (pathname === "/api/status" && method === "POST") {
      const body = await parseBody<StatusUpdate>(req);
      if (!body?.agent || !body?.message) {
        return json({ error: "agent and message required" }, 400);
      }

      const timestamp = body.timestamp || new Date().toISOString();
      const entry = { ...body, timestamp, lastSeen: timestamp };

      state.agents.set(body.agent, entry);
      state.log.push({ ...body, timestamp });

      if (state.log.length > 500) {
        state.log.splice(0, state.log.length - 500);
      }

      broadcast("status", entry);
      return json({ ok: true });
    }

    // --- Question from agent/orchestrator ---

    if (pathname === "/api/question" && method === "POST") {
      const body = await parseBody<{
        agent?: string;
        question: string;
        options?: string[];
      }>(req);
      if (!body?.question) {
        return json({ error: "question required" }, 400);
      }

      const question: Question = {
        id: `q-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        agent: body.agent || "orchestrator",
        question: body.question,
        options: body.options,
        timestamp: new Date().toISOString(),
        answered: false,
      };

      state.questions.push(question);
      broadcast("question", question);
      return json({ ok: true, id: question.id });
    }

    // --- User answer from dashboard UI ---

    if (pathname === "/api/answer" && method === "POST") {
      const body = await parseBody<{ id: string; answer: string }>(req);
      if (!body?.id || !body?.answer) {
        return json({ error: "id and answer required" }, 400);
      }

      const question = state.questions.find((q) => q.id === body.id);
      if (!question) {
        return json({ error: "question not found" }, 404);
      }

      question.answered = true;
      question.answer = body.answer;
      question.answeredAt = new Date().toISOString();

      broadcast("answer", question);
      return json({ ok: true });
    }

    // --- Pending answers (for orchestrator to poll) ---

    if (pathname === "/api/answers" && method === "GET") {
      const answered = state.questions.filter((q) => q.answered);
      return json(answered);
    }

    // --- Full state snapshot ---

    if (pathname === "/api/state") {
      return json({
        agents: Object.fromEntries(state.agents),
        questions: state.questions,
        log: state.log.slice(-100),
        startedAt: state.startedAt,
      });
    }

    // --- Reset state ---

    if (pathname === "/api/reset" && method === "POST") {
      state.agents.clear();
      state.questions.length = 0;
      state.log.length = 0;
      state.startedAt = new Date().toISOString();
      broadcast("reset", { startedAt: state.startedAt });
      return json({ ok: true });
    }

    // --- Shutdown ---

    if (pathname === "/api/shutdown" && method === "POST") {
      broadcast("shutdown", { message: "Dashboard shutting down" });
      setTimeout(() => process.exit(0), 100);
      return json({ ok: true });
    }

    return new Response("Not Found", { status: 404 });
  },
});

console.log(
  [
    "",
    "\x1b[35m◆\x1b[0m POF Dashboard",
    `  URL:     \x1b[36mhttp://localhost:${PORT}\x1b[0m`,
    `  Clients: ${sseClients.size} connected`,
    "  Press Ctrl+C to stop",
    "",
  ].join("\n")
);
