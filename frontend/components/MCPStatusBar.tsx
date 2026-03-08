"use client";

import { useEffect, useState } from "react";
import { GitBranch, MessageSquare, Users, Wifi, WifiOff } from "lucide-react";
import { clsx } from "clsx";
import { getMCPStatus } from "@/lib/api";

interface Integration {
  name: string;
  key: "github" | "slack" | "salesforce";
  icon: React.ElementType;
  detail?: string;
}

const INTEGRATIONS: Integration[] = [
  { name: "GitHub", key: "github", icon: GitBranch },
  { name: "Slack", key: "slack", icon: MessageSquare },
  { name: "Salesforce", key: "salesforce", icon: Users },
];

interface MCPHealth {
  status: "connected" | "error" | "loading";
  remaining?: number;
  team?: string;
  api_version?: string;
  error?: string;
}

export function MCPStatusBar() {
  const [health, setHealth] = useState<Record<string, MCPHealth>>({
    github: { status: "loading" },
    slack: { status: "loading" },
    salesforce: { status: "loading" },
  });

  useEffect(() => {
    async function fetchStatus() {
      try {
        const data = await getMCPStatus();
        setHealth({
          github: {
            status: data.github?.status === "connected" ? "connected" : "error",
            ...data.github,
          },
          slack: {
            status: data.slack?.status === "connected" ? "connected" : "error",
            ...data.slack,
          },
          salesforce: {
            status:
              data.salesforce?.status === "connected" ? "connected" : "error",
            ...data.salesforce,
          },
        });
      } catch {
        setHealth({
          github: { status: "error", error: "Unreachable" },
          slack: { status: "error", error: "Unreachable" },
          salesforce: { status: "error", error: "Unreachable" },
        });
      }
    }
    fetchStatus();
    const interval = setInterval(fetchStatus, 30_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="glass rounded-2xl p-5 border border-nexus-border">
      <p className="text-[10px] font-mono text-nexus-muted uppercase tracking-widest mb-4">
        MCP Integration Health
      </p>
      <div className="flex items-center gap-4">
        {INTEGRATIONS.map(({ name, key, icon: Icon }) => {
          const h = health[key];
          const connected = h.status === "connected";
          const loading = h.status === "loading";

          return (
            <div
              key={key}
              id={`mcp-status-${key}`}
              aria-label={`${name} integration status: ${h.status}`}
              className={clsx(
                "flex-1 flex items-center gap-3 px-4 py-3 rounded-xl border transition-all duration-300",
                connected && "bg-nexus-emerald/10 border-nexus-emerald/25",
                h.status === "error" && "bg-nexus-rose/10 border-nexus-rose/25",
                loading && "bg-white/5 border-nexus-border animate-pulse",
              )}
            >
              <Icon
                className={clsx(
                  "w-4 h-4",
                  connected && "text-nexus-emerald",
                  h.status === "error" && "text-nexus-rose",
                  loading && "text-nexus-muted",
                )}
              />
              <div className="min-w-0">
                <p className="text-xs font-semibold text-nexus-text">{name}</p>
                <p className="text-[10px] text-nexus-muted truncate">
                  {loading && "Checking…"}
                  {connected &&
                    (key === "github"
                      ? `${h.remaining ?? "–"} req remaining`
                      : key === "slack"
                      ? h.team ?? "Connected"
                      : h.api_version ?? "Connected")}
                  {h.status === "error" && (h.error ?? "Error")}
                </p>
              </div>
              <div className="ml-auto">
                {loading ? (
                  <div className="w-2 h-2 rounded-full bg-nexus-muted animate-ping" />
                ) : connected ? (
                  <Wifi className="w-3.5 h-3.5 text-nexus-emerald" />
                ) : (
                  <WifiOff className="w-3.5 h-3.5 text-nexus-rose" />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
