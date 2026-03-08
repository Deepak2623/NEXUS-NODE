"use client";

import { Activity, CheckCircle2, Clock, AlertTriangle } from "lucide-react";
import { clsx } from "clsx";

interface LiveMeshProps {
  nodeStatus: Record<string, string>;
}

const STATUS_COLOR: Record<string, string> = {
  pending: "border-nexus-border bg-white/5 text-nexus-muted",
  running: "border-nexus-accent/50 bg-nexus-accent/15 text-nexus-accent-glow",
  done: "border-nexus-emerald/50 bg-nexus-emerald/15 text-nexus-emerald",
  error: "border-nexus-rose/50 bg-nexus-rose/15 text-nexus-rose",
};

export function LiveMesh({ nodeStatus }: LiveMeshProps) {
  const nodes = [
    { id: "node_plan", label: "Planner", provider: "Groq" },
    { id: "node_execute", label: "Executor", provider: "MCP" },
    { id: "node_verify", label: "Verifier", provider: "Gemini" },
  ];

  return (
    <div className="flex flex-col items-center justify-center py-8 space-y-12 relative overflow-hidden">
      {/* Background Grid */}
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage:
            "linear-gradient(rgba(99,102,241,1) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,1) 1px, transparent 1px)",
          backgroundSize: "30px 30px",
        }}
      />

      {/* SVG Connectors */}
      <svg
        className="absolute inset-0 w-full h-full pointer-events-none"
        aria-hidden="true"
      >
        <defs>
          <marker
            id="arrow"
            viewBox="0 0 10 10"
            refX="5"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto-start-reverse"
          >
            <path
              d="M 0 0 L 10 5 L 0 10 z"
              fill="currentColor"
              className="text-nexus-border opacity-30"
            />
          </marker>
        </defs>
        <line
          x1="50%"
          y1="125"
          x2="50%"
          y2="175"
          stroke="currentColor"
          strokeWidth="1"
          markerEnd="url(#arrow)"
          className="text-nexus-border opacity-30"
        />
        <line
          x1="50%"
          y1="265"
          x2="50%"
          y2="315"
          stroke="currentColor"
          strokeWidth="1"
          markerEnd="url(#arrow)"
          className="text-nexus-border opacity-30"
        />
        {/* Loop back */}
        <path
          d="M 40% 380 Q 20% 240 40% 100"
          fill="none"
          stroke="currentColor"
          strokeWidth="1"
          strokeDasharray="4 4"
          markerEnd="url(#arrow)"
          className="text-nexus-accent/20"
        />
      </svg>

      <div className="relative z-10 space-y-16">
        {nodes.map((node) => {
          const status = nodeStatus[node.id] || "pending";
          const Icon =
            status === "running"
              ? Activity
              : status === "done"
              ? CheckCircle2
              : status === "error"
              ? AlertTriangle
              : Clock;

          return (
            <div
              key={node.id}
              className={clsx(
                "relative w-64 rounded-2xl border p-4 transition-all duration-500 shadow-nexus-sm",
                STATUS_COLOR[status],
                status === "running" && "scale-105 shadow-nexus-md",
              )}
            >
              {status === "running" && (
                <div className="absolute -inset-px rounded-2xl bg-nexus-accent/10 animate-pulse pointer-events-none" />
              )}
              <div className="flex items-center gap-3 mb-2">
                <div
                  className={clsx(
                    "p-1.5 rounded-lg bg-white/5",
                    status === "running" && "animate-spin-slow",
                  )}
                >
                  <Icon className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-bold font-mono uppercase tracking-wider">
                    {node.label}
                  </h4>
                  <p className="text-[10px] opacity-60 font-mono">
                    {node.provider}
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-between text-[10px] font-mono mt-3 pt-3 border-t border-white/5 uppercase tracking-widest opacity-40">
                <span>Status</span>
                <span
                  className={clsx(
                    "font-bold",
                    status === "running" && "animate-pulse",
                  )}
                >
                  {status}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
