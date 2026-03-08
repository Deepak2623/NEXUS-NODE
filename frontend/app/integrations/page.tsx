"use client";

import { useEffect, useState } from "react";
import {
  GitBranch,
  MessageSquare,
  RefreshCw,
  Users,
  Wifi,
  WifiOff,
} from "lucide-react";
import { clsx } from "clsx";
import { getMCPStatus } from "@/lib/api";

interface IntegrationDetail {
  key: string;
  name: string;
  icon: React.ElementType;
  description: string;
  scopes: string[];
  hitlRequired: string[];
}

const INTEGRATIONS: IntegrationDetail[] = [
  {
    key: "github",
    name: "GitHub",
    icon: GitBranch,
    description: "Repository read, PR creation and merge via GitHub REST API.",
    scopes: ["repo:read", "pull_requests:write (HITL)"],
    hitlRequired: ["git push", "PR merge", "force push"],
  },
  {
    key: "slack",
    name: "Slack",
    icon: MessageSquare,
    description:
      "Post messages, list channels, and reply in threads via Slack Web API.",
    scopes: ["chat:write", "channels:read"],
    hitlRequired: ["Bulk message broadcast"],
  },
  {
    key: "salesforce",
    name: "Salesforce",
    icon: Users,
    description:
      "SOQL account queries and Opportunity record updates via REST API v59.0.",
    scopes: ["API (read)", "API (write, HITL-gated)"],
    hitlRequired: ["record updates", "bulk mutations > 10 records"],
  },
];

export default function IntegrationsPage() {
  const [health, setHealth] = useState<Record<string, Record<string, unknown>>>(
    {},
  );
  const [loading, setLoading] = useState(true);

  async function fetchHealth() {
    setLoading(true);
    try {
      const data = await getMCPStatus();
      setHealth(data);
    } catch {
      setHealth({});
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchHealth();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 lg:space-y-8 animate-fade-in">
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-nexus-muted text-xs font-mono uppercase tracking-widest">
            <GitBranch className="w-3 h-3" />
            <span>MCP Integrations</span>
          </div>
          <h1 className="text-3xl font-bold text-nexus-text text-glow-indigo">
            Integration Status
          </h1>
          <p className="text-nexus-text-dim text-sm">
            GitHub · Slack · Salesforce — all via Model Context Protocol with
            least-privilege scopes
          </p>
        </div>
        <button
          id="refresh-integrations-btn"
          aria-label="Refresh integration status"
          onClick={fetchHealth}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold border border-nexus-border text-nexus-text hover:bg-white/5 transition-all"
        >
          <RefreshCw
            className={clsx("w-3.5 h-3.5", loading && "animate-spin")}
          />
          Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 gap-6">
        {INTEGRATIONS.map(
          ({ key, name, icon: Icon, description, scopes, hitlRequired }) => {
            const h = health[key] ?? {};
            const connected = h.status === "connected";
            const isLoading = !Object.keys(health).length || loading;

            return (
              <div
                key={key}
                id={`integration-card-${key}`}
                className="glass border-gradient rounded-2xl p-6 hover:shadow-nexus-md transition-all duration-300"
              >
                <div className="flex items-start gap-5">
                  {/* Icon */}
                  <div
                    className={clsx(
                      "p-3 rounded-xl border transition-all",
                      connected
                        ? "bg-nexus-emerald/15 border-nexus-emerald/30"
                        : "bg-white/5 border-nexus-border",
                    )}
                  >
                    <Icon
                      className={clsx(
                        "w-5 h-5",
                        connected ? "text-nexus-emerald" : "text-nexus-muted",
                      )}
                    />
                  </div>

                  {/* Info */}
                  <div className="flex-1 space-y-3">
                    <div className="flex items-center gap-3">
                      <h2 className="text-base font-semibold text-nexus-text">
                        {name}
                      </h2>
                      {isLoading ? (
                        <span className="px-2 py-0.5 rounded-full bg-white/5 text-nexus-muted text-xs font-mono animate-pulse">
                          checking…
                        </span>
                      ) : connected ? (
                        <span className="px-2 py-0.5 rounded-full bg-nexus-emerald/15 border border-nexus-emerald/30 text-nexus-emerald text-xs font-mono flex items-center gap-1.5">
                          <Wifi className="w-3 h-3" /> Connected
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full bg-nexus-rose/15 border border-nexus-rose/30 text-nexus-rose text-xs font-mono flex items-center gap-1.5">
                          <WifiOff className="w-3 h-3" />{" "}
                          {String(h.error ?? "Disconnected")}
                        </span>
                      )}
                    </div>

                    <p className="text-nexus-text-dim text-sm">{description}</p>

                    <div className="flex gap-6">
                      <div>
                        <p className="text-[10px] font-mono text-nexus-muted uppercase tracking-wider mb-1.5">
                          API Scopes
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {scopes.map((s) => (
                            <span
                              key={s}
                              className="px-2 py-0.5 rounded bg-nexus-accent/10 border border-nexus-accent/20 text-nexus-accent-glow text-[10px] font-mono"
                            >
                              {s}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-[10px] font-mono text-nexus-muted uppercase tracking-wider mb-1.5">
                          HITL Required
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {hitlRequired.map((a) => (
                            <span
                              key={a}
                              className="px-2 py-0.5 rounded bg-nexus-amber/10 border border-nexus-amber/20 text-nexus-amber text-[10px] font-mono"
                            >
                              {a}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Live details */}
                    {connected && (
                      <div className="mt-2 flex gap-4 text-[10px] font-mono text-nexus-muted">
                        {key === "github" && h.remaining !== undefined && (
                          <span>
                            Rate limit remaining:{" "}
                            <span className="text-nexus-cyan">
                              {String(h.remaining)}
                            </span>{" "}
                            / {String(h.limit)}
                          </span>
                        )}
                        {key === "slack" && Boolean(h.team) && (
                          <span>
                            Team:{" "}
                            <span className="text-nexus-cyan">
                              {String(h.team)}
                            </span>{" "}
                            · User: {String(h.user)}
                          </span>
                        )}
                        {key === "salesforce" && Boolean(h.api_version) && (
                          <span>
                            API:{" "}
                            <span className="text-nexus-cyan">
                              {String(h.api_version)}
                            </span>
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          },
        )}
      </div>
    </div>
  );
}
