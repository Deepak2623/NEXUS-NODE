"use client";

import { useEffect, useState } from "react";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Clock,
  Network,
  RefreshCw,
} from "lucide-react";
import { clsx } from "clsx";

interface NodeState {
  id: string;
  label: string;
  role: string;
  provider: string;
  status: "pending" | "running" | "done" | "error";
  x: number;
  y: number;
}

const INITIAL_NODES: NodeState[] = [
  {
    id: "node_plan",
    label: "node_plan",
    role: "Planner",
    provider: "Groq Llama-3.3-70b",
    status: "pending",
    x: 160,
    y: 80,
  },
  {
    id: "node_execute",
    label: "node_execute",
    role: "Tool Dispatcher",
    provider: "MCP Registry",
    status: "pending",
    x: 160,
    y: 240,
  },
  {
    id: "node_verify",
    label: "node_verify",
    role: "Verifier",
    provider: "Gemini 2.5 Flash",
    status: "pending",
    x: 160,
    y: 400,
  },
  {
    id: "governor",
    label: "GovernorNode",
    role: "PII + Audit",
    provider: "Rule-based",
    status: "done",
    x: 420,
    y: 240,
  },
];

const STATUS_COLOR: Record<string, string> = {
  pending: "border-nexus-border bg-white/5 text-nexus-muted",
  running: "border-nexus-accent/50 bg-nexus-accent/15 text-nexus-accent-glow",
  done: "border-nexus-emerald/50 bg-nexus-emerald/15 text-nexus-emerald",
  error: "border-nexus-rose/50 bg-nexus-rose/15 text-nexus-rose",
};

export default function MeshPage() {
  const [nodes, setNodes] = useState<NodeState[]>(INITIAL_NODES);
  const [animating, setAnimating] = useState(false);

  function simulateCycle() {
    setAnimating(true);
    const sequence: Array<[string, NodeState["status"]]> = [
      ["node_plan", "running"],
      ["node_plan", "done"],
      ["node_execute", "running"],
      ["node_execute", "done"],
      ["node_verify", "running"],
      ["node_verify", "done"],
    ];

    // Reset first
    setNodes(
      INITIAL_NODES.map((n) => ({
        ...n,
        status: n.id === "governor" ? "done" : "pending",
      })),
    );

    sequence.forEach(([id, status], i) => {
      setTimeout(() => {
        setNodes((prev) =>
          prev.map((n) => (n.id === id ? { ...n, status } : n)),
        );
        if (i === sequence.length - 1) setAnimating(false);
      }, (i + 1) * 800);
    });
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 lg:space-y-8 animate-fade-in">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-nexus-muted text-xs font-mono uppercase tracking-widest">
            <Network className="w-3 h-3" />
            <span>Live Mesh Graph</span>
          </div>
          <h1 className="text-3xl font-bold text-nexus-text text-glow-indigo">
            Action Mesh Topology
          </h1>
          <p className="text-nexus-text-dim text-sm">
            Real-time LangGraph cyclic state machine — plan → execute → verify
            loop
          </p>
        </div>
        <button
          id="simulate-cycle-btn"
          aria-label="Simulate mesh cycle"
          onClick={simulateCycle}
          disabled={animating}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-br from-nexus-accent to-indigo-600 text-white hover:shadow-nexus-md transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={clsx("w-4 h-4", animating && "animate-spin")} />
          Simulate Cycle
        </button>
      </div>

      {/* SVG Mesh Canvas */}
      <div className="glass border-gradient rounded-2xl p-8 relative overflow-hidden min-h-[520px]">
        {/* Background grid */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage:
              "linear-gradient(rgba(99,102,241,1) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,1) 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />

        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          aria-hidden="true"
        >
          {/* Connectors: plan → execute → verify */}
          <line x1="240" y1="120" x2="240" y2="220" className="connector" />
          <line x1="240" y1="280" x2="240" y2="380" className="connector" />
          {/* verify → plan loop */}
          <path
            d="M 200 440 Q 60 300 200 120"
            fill="none"
            className="connector"
          />
          {/* Governor connections */}
          <line x1="310" y1="120" x2="400" y2="220" className="connector" />
          <line x1="310" y1="270" x2="400" y2="260" className="connector" />
          <line x1="310" y1="420" x2="400" y2="270" className="connector" />
        </svg>

        <div className="relative z-10 flex gap-24 justify-center items-start pt-4">
          {/* Main chain */}
          <div className="flex flex-col items-center gap-16">
            {nodes
              .filter((n) => n.id !== "governor")
              .map((node) => (
                <MeshNode key={node.id} node={node} />
              ))}
          </div>

          {/* Governor */}
          <div className="flex items-center" style={{ marginTop: "140px" }}>
            {nodes
              .filter((n) => n.id === "governor")
              .map((node) => (
                <MeshNode key={node.id} node={node} highlight />
              ))}
          </div>
        </div>

        {/* Legend */}
        <div className="absolute bottom-4 right-4 flex items-center gap-4 text-[10px] font-mono text-nexus-muted">
          {(["pending", "running", "done", "error"] as const).map((s) => (
            <div key={s} className="flex items-center gap-1.5">
              <span
                className={clsx("w-2 h-2 rounded-sm border", STATUS_COLOR[s])}
              />
              {s}
            </div>
          ))}
        </div>
      </div>

      {/* Node detail table */}
      <div className="glass rounded-2xl overflow-hidden border border-nexus-border">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-nexus-border bg-white/[0.02]">
              {["Node", "Role", "Provider", "Status"].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs text-nexus-muted font-mono uppercase tracking-wider"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {nodes.map((node) => (
              <tr
                key={node.id}
                className="border-b border-nexus-border/50 hover:bg-white/[0.02] transition-colors"
              >
                <td className="px-4 py-3 font-mono text-nexus-accent-glow text-xs">
                  {node.label}
                </td>
                <td className="px-4 py-3 text-nexus-text-dim">{node.role}</td>
                <td className="px-4 py-3 text-nexus-text-dim text-xs">
                  {node.provider}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={clsx(
                      "px-2.5 py-1 rounded-lg text-xs border font-mono",
                      STATUS_COLOR[node.status],
                    )}
                  >
                    {node.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MeshNode({
  node,
  highlight = false,
}: {
  node: NodeState;
  highlight?: boolean;
}) {
  const STATUS_ICON: Record<string, React.ElementType> = {
    pending: Clock,
    running: Activity,
    done: CheckCircle2,
    error: ArrowRight,
  };
  const Icon = STATUS_ICON[node.status];

  return (
    <div
      id={`mesh-node-${node.id}`}
      aria-label={`${node.label} — ${node.status}`}
      className={clsx(
        "relative w-52 rounded-2xl border p-4 transition-all duration-500",
        STATUS_COLOR[node.status],
        node.status === "running" && "shadow-nexus-md scale-[1.02]",
        highlight && "w-48",
      )}
    >
      {node.status === "running" && (
        <div className="absolute -inset-px rounded-2xl bg-nexus-accent/20 animate-pulse pointer-events-none" />
      )}
      <div className="flex items-center gap-2 mb-2">
        <Icon
          className={clsx(
            "w-3.5 h-3.5",
            node.status === "running" && "animate-spin",
          )}
        />
        <span className="text-xs font-mono font-semibold">{node.label}</span>
      </div>
      <p className="text-[10px] opacity-70">{node.role}</p>
      <p className="text-[10px] opacity-50 font-mono mt-0.5">{node.provider}</p>
    </div>
  );
}
