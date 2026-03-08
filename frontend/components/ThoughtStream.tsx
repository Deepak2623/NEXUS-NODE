"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  RefreshCw,
  Shield,
} from "lucide-react";
import { clsx } from "clsx";
import Link from "next/link";
import { useSSE } from "@/lib/sse";
import { approveHITL, rejectHITL } from "@/lib/api";

interface ThoughtStreamProps {
  taskId: string;
}

interface SSEEvent {
  type: string;
  data?: {
    phase?: string;
    node_status?: Record<string, string>;
    plan?: string[];
    iteration_count?: number;
    hitl_required?: boolean;
    verification_result?: string;
    message?: string;
  };
}

import { ArrowRight, Layout, MessageSquare, Network } from "lucide-react";
import { LiveMesh } from "./LiveMesh";

export function ThoughtStream({ taskId }: ThoughtStreamProps) {
  const [activeTab, setActiveTab] = useState<"logs" | "graph">("logs");
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [nodeStatus, setNodeStatus] = useState<Record<string, string>>({
    node_plan: "pending",
    node_execute: "pending",
    node_verify: "pending",
  });
  const [plan, setPlan] = useState<string[]>([]);
  const [latestMessage, setLatestMessage] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [hitlDecision, setHitlDecision] = useState<
    "pending" | "approved" | "rejected"
  >("pending");
  const scrollRef = { current: null as HTMLDivElement | null };

  const { connect, disconnect } = useSSE(
    `/api/backend/stream/${taskId}`,
    (raw) => {
      const parsed: SSEEvent =
        typeof raw === "string" ? JSON.parse(raw) : (raw as SSEEvent);
      setEvents((prev) => [...prev.slice(-200), parsed]);
      if (parsed.data?.node_status) setNodeStatus(parsed.data.node_status);
      if (parsed.data?.plan?.length) setPlan(parsed.data.plan);
      if (parsed.data?.message) setLatestMessage(parsed.data.message);
      if (parsed.data?.phase === "completed" || parsed.type === "error")
        setDone(true);
    },
  );

  useEffect(() => {
    // Reset state for new task
    setEvents([]);
    setNodeStatus({
      node_plan: "pending",
      node_execute: "pending",
      node_verify: "pending",
    });
    setPlan([]);
    setLatestMessage(null);
    setDone(false);
    setHitlDecision("pending");

    connect();
    return () => disconnect();
  }, [taskId]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleHITL = async (action: "approve" | "reject") => {
    try {
      if (action === "approve") await approveHITL(taskId);
      else await rejectHITL(taskId);
      setHitlDecision(action === "approve" ? "approved" : "rejected");
    } catch (e) {
      console.error(e);
    }
  };

  const NODE_META: Record<string, { label: string }> = {
    node_plan: { label: "node_plan (Groq)" },
    node_execute: { label: "node_execute (Tools)" },
    node_verify: { label: "node_verify (Gemini)" },
  };

  return (
    <div className="glass border-gradient rounded-2xl p-4 sm:p-6 space-y-5">
      {/* Header with Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/5 pb-4">
        <div className="flex items-center gap-4">
          <button
            onClick={() => setActiveTab("logs")}
            className={clsx(
              "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all",
              activeTab === "logs"
                ? "bg-nexus-accent/20 text-nexus-accent-glow"
                : "text-nexus-muted hover:text-nexus-text hover:bg-white/5",
            )}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Streaming Logs
          </button>
          <button
            onClick={() => setActiveTab("graph")}
            className={clsx(
              "flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all",
              activeTab === "graph"
                ? "bg-nexus-accent/20 text-nexus-accent-glow"
                : "text-nexus-muted hover:text-nexus-text hover:bg-white/5",
            )}
          >
            <Network className="w-3.5 h-3.5" />
            Live Graph Mesh
          </button>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {Object.entries(nodeStatus).map(([node, status]) => {
            const meta = NODE_META[node] ?? { label: node };
            return (
              <div
                key={node}
                title={meta.label}
                className={clsx(
                  "w-2 h-2 rounded-full border transition-all",
                  status === "done" &&
                    "bg-nexus-emerald border-nexus-emerald/30 shadow-[0_0_8px_rgba(16,185,129,0.5)]",
                  status === "running" &&
                    "bg-nexus-accent border-nexus-accent/30 animate-pulse shadow-[0_0_8px_rgba(99,102,241,0.5)]",
                  status === "error" && "bg-nexus-rose border-nexus-rose/30",
                  status === "pending" && "bg-white/10 border-white/5",
                )}
              />
            );
          })}
          {done && (
            <span className="ml-2 text-[10px] text-nexus-emerald font-mono font-bold uppercase tracking-widest">
              Complete
            </span>
          )}
        </div>
      </div>

      {activeTab === "graph" ? (
        <div className="animate-fade-in py-4 bg-black/20 rounded-xl border border-white/5">
          <LiveMesh nodeStatus={nodeStatus} />
        </div>
      ) : (
        <div className="space-y-5 animate-fade-in">
          {/* HITL Banner */}
          {events.some((e) => e.data?.hitl_required) && !done && (
            <div className="bg-nexus-amber/10 border border-nexus-amber/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4 animate-pulse">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-nexus-amber/20">
                  <Shield className="w-5 h-5 text-nexus-amber" />
                </div>
                <div>
                  <p className="text-sm font-bold text-nexus-amber">
                    {hitlDecision === "pending"
                      ? "Action Requires Approval"
                      : hitlDecision === "approved"
                      ? "Approval Received — Resuming Mesh Cycle..."
                      : "Action Declined — Halting Task..."}
                  </p>
                  <p className="text-[10px] text-nexus-amber/70 font-mono">
                    {hitlDecision === "pending"
                      ? "The mesh is requesting permission to execute restricted tools."
                      : "Cryptographic audit ledger is being signed & updated..."}
                  </p>
                </div>
              </div>
              {hitlDecision === "pending" ? (
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleHITL("approve")}
                    className="px-4 py-2 rounded-lg bg-nexus-emerald text-white text-xs font-bold hover:scale-105 transition-transform shadow-nexus-emerald-sm"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => handleHITL("reject")}
                    className="px-4 py-2 rounded-lg bg-nexus-rose text-white text-xs font-bold hover:scale-105 transition-transform shadow-nexus-rose-sm"
                  >
                    Decline
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-xs font-bold font-mono px-4 py-2 rounded-lg border border-white/10 bg-white/5">
                  {hitlDecision === "approved" ? (
                    <span className="text-nexus-emerald">✓ Accepted</span>
                  ) : (
                    <span className="text-nexus-rose">✗ Declined</span>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Latest AI Output */}
          {latestMessage && (
            <div className="space-y-2 animate-fade-in">
              <p className="text-[10px] font-mono text-nexus-muted uppercase tracking-widest">
                Latest Result / Thought
              </p>
              <div className="bg-white/5 border border-white/10 rounded-xl p-4 text-sm font-mono whitespace-pre-wrap">
                {(() => {
                  if (
                    latestMessage.startsWith("Error code:") ||
                    latestMessage.includes("tool_use_failed")
                  ) {
                    const toolMatch = latestMessage.match(/<function=([^>]+)>/);
                    const msgMatch = latestMessage.match(
                      /'message':\s*"([^"]+)"/,
                    );
                    const niceMsg = msgMatch
                      ? msgMatch[1]
                      : "The Agent encountered an API error.";
                    const toolName = toolMatch ? toolMatch[1] : "unknown_tool";

                    return (
                      <div className="text-nexus-rose space-y-2">
                        <div className="flex items-center gap-2 font-bold">
                          <AlertTriangle className="w-4 h-4" /> Agent Execution
                          Failed
                        </div>
                        <p className="text-xs">
                          <strong>Reason:</strong> {niceMsg}
                        </p>
                        {toolName !== "unknown_tool" && (
                          <p className="text-xs">
                            <strong>Failed Tool:</strong>{" "}
                            <code>{toolName}</code>
                          </p>
                        )}
                        <details className="mt-3 text-[10px] opacity-80 cursor-pointer">
                          <summary>View raw error trace</summary>
                          <pre className="mt-2 p-2 bg-black/30 rounded overflow-x-auto">
                            {latestMessage}
                          </pre>
                        </details>
                      </div>
                    );
                  }
                  return (
                    <span className="text-nexus-text">{latestMessage}</span>
                  );
                })()}
              </div>
            </div>
          )}

          {/* Plan steps */}
          {plan.length > 0 && (
            <div className="space-y-1">
              <p className="text-[10px] font-mono text-nexus-muted uppercase tracking-widest">
                Execution Plan
              </p>
              {plan.map((step, i) => (
                <div
                  key={i}
                  className="flex items-start gap-2 text-xs text-nexus-text-dim font-mono"
                >
                  <span className="text-nexus-accent shrink-0">
                    {String(i + 1).padStart(2, "0")}.
                  </span>
                  <span className="break-words">{step}</span>
                </div>
              ))}
            </div>
          )}

          {/* Event log */}
          <div
            ref={(el) => {
              scrollRef.current = el;
            }}
            className="h-40 sm:h-48 overflow-y-auto rounded-xl bg-nexus-bg border border-nexus-border p-3 space-y-1 scan-overlay relative"
          >
            {events.length === 0 && (
              <p className="text-nexus-muted text-xs font-mono opacity-50 flex items-center gap-2">
                <RefreshCw className="w-3 h-3 animate-spin" /> Connecting to SSE
                stream…
              </p>
            )}
            {events.map((ev, i) => (
              <div key={i} className="thought-stream break-all text-[10px]">
                <span className="text-nexus-muted opacity-50">
                  [{ev.type}]{" "}
                </span>
                <span>
                  {ev.data?.message ? (
                    <span className="text-nexus-cyan">{ev.data.message}</span>
                  ) : (
                    JSON.stringify(ev.data)
                  )}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
