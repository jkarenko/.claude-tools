/**
 * POF Dashboard Server
 *
 * Real-time monitoring for POF agent workflow.
 * Supports multiple concurrent sessions routed by session ID.
 * Zero dependencies — runs on Bun's built-in HTTP server.
 *
 * Start:  bun run dashboard/server.ts
 * View:   http://localhost:3456
 * Stop:   Ctrl+C or POST /api/shutdown
 */

const PORT = parseInt(process.env.POF_DASHBOARD_PORT || "3456");
const SESSION_TTL = 4 * 60 * 60 * 1000; // 4 hours — auto-expire stale sessions

// --- Types ---

interface StatusUpdate {
  agent: string;
  session?: string;
  phase?: string;
  status?: "started" | "working" | "complete" | "error" | "blocked";
  message: string;
  detail?: string;
  timestamp?: string;
}

interface Question {
  id: string;
  session: string;
  agent: string;
  question: string;
  options?: string[];
  timestamp: string;
  answered: boolean;
  answer?: string;
  answeredAt?: string;
}

interface SessionState {
  id: string;
  project?: string;
  agents: Map<string, StatusUpdate & { lastSeen: string }>;
  questions: Question[];
  log: (StatusUpdate & { timestamp: string })[];
  startedAt: string;
  lastActivity: string;
}

// --- State (in-memory, ephemeral) ---

const sessions = new Map<string, SessionState>();
const serverStartedAt = new Date().toISOString();

function getOrCreateSession(id: string): SessionState {
  let session = sessions.get(id);
  if (!session) {
    session = {
      id,
      agents: new Map(),
      questions: [],
      log: [],
      startedAt: new Date().toISOString(),
      lastActivity: new Date().toISOString(),
    };
    sessions.set(id, session);
    broadcast("session-new", { id: session.id, startedAt: session.startedAt });
  }
  return session;
}

function touchSession(session: SessionState) {
  session.lastActivity = new Date().toISOString();
}

// Auto-expire stale sessions
setInterval(() => {
  const now = Date.now();
  for (const [id, session] of sessions) {
    if (now - new Date(session.lastActivity).getTime() > SESSION_TTL) {
      sessions.delete(id);
      broadcast("session-removed", { id });
    }
  }
}, 60 * 1000);

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

function sessionSummary(s: SessionState) {
  const activeAgents = [...s.agents.values()].filter(
    (a) => a.status === "working" || a.status === "started"
  ).length;
  const pendingQuestions = s.questions.filter((q) => !q.answered).length;
  let currentPhase = "0";
  for (const a of s.agents.values()) {
    if (a.phase) {
      const p = a.phase.split(".")[0];
      if (parseInt(p) > parseInt(currentPhase)) currentPhase = p;
    }
  }
  return {
    id: s.id,
    project: s.project,
    startedAt: s.startedAt,
    lastActivity: s.lastActivity,
    currentPhase,
    activeAgents,
    totalAgents: s.agents.size,
    pendingQuestions,
  };
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
      const uptime =
        (Date.now() - new Date(serverStartedAt).getTime()) / 1000;
      return json({
        ok: true,
        uptime: Math.round(uptime),
        clients: sseClients.size,
        sessions: sessions.size,
      });
    }

    // --- List sessions ---

    if (pathname === "/api/sessions") {
      return json([...sessions.values()].map(sessionSummary));
    }

    // --- SSE event stream ---

    if (pathname === "/api/events") {
      const stream = new ReadableStream({
        start(controller) {
          sseClients.add(controller);

          // Send init with all sessions
          const sessionsData: Record<string, unknown> = {};
          for (const [id, s] of sessions) {
            sessionsData[id] = {
              ...sessionSummary(s),
              agents: Object.fromEntries(s.agents),
              questions: s.questions,
              log: s.log.slice(-100),
            };
          }

          const init = encoder.encode(
            `event: init\ndata: ${JSON.stringify({
              sessions: sessionsData,
              serverStartedAt,
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

      const sessionId = body.session || url.searchParams.get("session") || "default";
      const session = getOrCreateSession(sessionId);
      touchSession(session);

      if (body.detail?.startsWith("project:")) {
        session.project = body.detail.replace("project:", "").trim();
      }

      const timestamp = body.timestamp || new Date().toISOString();
      const entry = { ...body, session: sessionId, timestamp, lastSeen: timestamp };

      session.agents.set(body.agent, entry);
      session.log.push({ ...body, session: sessionId, timestamp });

      if (session.log.length > 500) {
        session.log.splice(0, session.log.length - 500);
      }

      broadcast("status", entry);
      return json({ ok: true });
    }

    // --- Question from agent/orchestrator ---

    if (pathname === "/api/question" && method === "POST") {
      const body = await parseBody<{
        agent?: string;
        session?: string;
        question: string;
        options?: string[];
      }>(req);
      if (!body?.question) {
        return json({ error: "question required" }, 400);
      }

      const sessionId = body.session || url.searchParams.get("session") || "default";
      const session = getOrCreateSession(sessionId);
      touchSession(session);

      const question: Question = {
        id: `q-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        session: sessionId,
        agent: body.agent || "orchestrator",
        question: body.question,
        options: body.options,
        timestamp: new Date().toISOString(),
        answered: false,
      };

      session.questions.push(question);
      broadcast("question", question);
      return json({ ok: true, id: question.id });
    }

    // --- User answer from dashboard UI ---

    if (pathname === "/api/answer" && method === "POST") {
      const body = await parseBody<{ id: string; answer: string; session?: string }>(req);
      if (!body?.id || !body?.answer) {
        return json({ error: "id and answer required" }, 400);
      }

      // Search all sessions for the question
      for (const session of sessions.values()) {
        const question = session.questions.find((q) => q.id === body.id);
        if (question) {
          question.answered = true;
          question.answer = body.answer;
          question.answeredAt = new Date().toISOString();
          touchSession(session);
          broadcast("answer", question);
          return json({ ok: true });
        }
      }

      return json({ error: "question not found" }, 404);
    }

    // --- Pending answers (for orchestrator to poll) ---

    if (pathname === "/api/answers" && method === "GET") {
      const sessionId = url.searchParams.get("session");
      if (sessionId) {
        const session = sessions.get(sessionId);
        if (!session) return json([]);
        return json(session.questions.filter((q) => q.answered));
      }
      // All answered questions across all sessions
      const all: Question[] = [];
      for (const s of sessions.values()) {
        all.push(...s.questions.filter((q) => q.answered));
      }
      return json(all);
    }

    // --- Full state snapshot for a session ---

    if (pathname === "/api/state") {
      const sessionId = url.searchParams.get("session");
      if (sessionId) {
        const session = sessions.get(sessionId);
        if (!session) return json({ error: "session not found" }, 404);
        return json({
          ...sessionSummary(session),
          agents: Object.fromEntries(session.agents),
          questions: session.questions,
          log: session.log.slice(-100),
        });
      }
      // Return all sessions
      const all: Record<string, unknown> = {};
      for (const [id, s] of sessions) {
        all[id] = {
          ...sessionSummary(s),
          agents: Object.fromEntries(s.agents),
          questions: s.questions,
          log: s.log.slice(-100),
        };
      }
      return json({ sessions: all, serverStartedAt });
    }

    // --- Reset a session or all sessions ---

    if (pathname === "/api/reset" && method === "POST") {
      const sessionId = url.searchParams.get("session");
      if (sessionId) {
        sessions.delete(sessionId);
        broadcast("session-removed", { id: sessionId });
      } else {
        sessions.clear();
        broadcast("reset", { serverStartedAt });
      }
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
