"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Clock,
  Layers,
  Send,
  Shield,
  Zap,
} from "lucide-react";
import { clsx } from "clsx";
import { MCPStatusBar } from "@/components/MCPStatusBar";
import { ThoughtStream } from "@/components/ThoughtStream";
import { runTask, getTasks, getAuditLog, clearTasks } from "@/lib/api";
import Link from "next/link";

export default function DashboardPage() {
  const [task, setTask] = useState("");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState({
    tasksToday: "0",
    auditEntries: "0",
    hitlEvents: "0",
  });
  const [recentTasks, setRecentTasks] = useState<any[]>([]);
  const [totalTasks, setTotalTasks] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);

  const fetchStats = useCallback(async () => {
    try {
      const [tasksRes, auditRes, healthRes] = await Promise.all([
        getTasks(currentPage, 20).catch(() => ({ tasks: [], count: 0 })),
        getAuditLog(1, 10).catch(() => ({ entries: [], count: 0 })),
        fetch("/api/backend/health")
          .then((r) => r.json())
          .catch(() => ({ pending_hitl_count: 0 })),
      ]);

      setStats({
        tasksToday: String((tasksRes as any).count || 0),
        auditEntries: String((auditRes as any).count || 0),
        hitlEvents: String(healthRes.pending_hitl_count || 0),
      });

      setRecentTasks((tasksRes as any).tasks || []);
      setTotalTasks((tasksRes as any).count || 0);
    } catch (err) {
      console.error("Failed to load stats", err);
    }
  }, [currentPage]);

  useEffect(() => {
    fetchStats();
    // Check for taskId in URL (from Governance re-inspect)
    const params = new URLSearchParams(window.location.search);
    const id = params.get("taskId");
    if (id) setTaskId(id);
  }, [fetchStats]);

  async function handleRun() {
    if (!task.trim()) return;
    setLoading(true);
    setError(null);
    setTaskId(null); // Clear old task view immediately
    try {
      const response = await runTask({ task });
      setTaskId(response.task_id);
      setTask("");
      fetchStats();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start task");
    } finally {
      setLoading(false);
    }
  }

  const statCards = [
    {
      label: "Avg Latency",
      value: "~300ms",
      sub: "Groq node_plan P95",
      icon: Zap,
      color: "text-nexus-accent",
    },
    {
      label: "Tasks Today",
      value: stats.tasksToday,
      sub: "Active database",
      icon: Activity,
      color: "text-nexus-cyan",
    },
    {
      label: "Audit Entries",
      value: stats.auditEntries,
      sub: "Hashed proof",
      icon: Shield,
      color: "text-nexus-emerald",
    },
    {
      label: "HITL Events",
      value: stats.hitlEvents,
      sub: "Manual join",
      icon: Clock,
      color: "text-nexus-amber",
    },
  ];

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-6 animate-fade-in max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-nexus-muted text-xs font-mono uppercase tracking-widest">
            <Layers className="w-3 h-3" />
            <span>Action Mesh Dashboard</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-nexus-text text-glow-indigo">
            NEXUS-NODE Control Center
          </h1>
          <p className="text-nexus-text-dim text-sm max-w-2xl">
            Autonomous enterprise Action Mesh — High-fidelity task execution
            with live state mesh and cryptographic governance.
          </p>
        </div>
        <Link
          href="/governance"
          className={clsx(
            "flex items-center gap-2 px-5 py-2.5 rounded-xl border transition-all text-sm font-bold shadow-nexus-sm",
            Number(stats.hitlEvents) > 0
              ? "bg-nexus-amber/20 border-nexus-amber/50 text-nexus-amber animate-pulse shadow-nexus-amber-sm"
              : "bg-white/5 border-nexus-border text-nexus-text hover:bg-white/10",
          )}
        >
          View Governance Hub <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map(({ label, value, sub, icon: Icon, color }) => (
          <div
            key={label}
            className="glass border-gradient rounded-2xl p-5 hover:shadow-nexus-md transition-all duration-300 transform hover:-translate-y-1"
          >
            <div className="flex items-start justify-between mb-4">
              <div className={clsx("p-2 rounded-xl bg-white/5", color)}>
                <Icon className="w-4 h-4" />
              </div>
              <CheckCircle2 className="w-3.5 h-3.5 text-nexus-emerald opacity-60" />
            </div>
            <p className={clsx("text-2xl font-bold", color)}>{value}</p>
            <p className="text-nexus-text text-sm font-medium mt-0.5">
              {label}
            </p>
            <p className="text-nexus-muted text-[10px] uppercase tracking-wider mt-1">
              {sub}
            </p>
          </div>
        ))}
      </div>

      {/* MCP Status */}
      <MCPStatusBar />

      {/* Task Runner */}
      <div className="glass border-gradient rounded-2xl p-4 sm:p-6 space-y-4 shadow-nexus-sm relative overflow-hidden">
        <div className="flex items-center gap-2 relative z-10">
          <Zap className="w-4 h-4 text-nexus-accent" />
          <h2 className="text-base font-semibold text-nexus-text">
            Run a Mesh Task
          </h2>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 relative z-10">
          <textarea
            id="task-input"
            aria-label="Task description"
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="Describe what you want the mesh to do..."
            rows={3}
            className="flex-1 bg-nexus-bg/50 backdrop-blur border border-nexus-border rounded-xl px-4 py-3 text-sm text-nexus-text placeholder:text-nexus-muted focus:outline-none focus:border-nexus-accent/50 focus:shadow-nexus-sm transition-all resize-none font-mono"
          />
          <button
            id="run-task-btn"
            aria-label="Run task"
            onClick={handleRun}
            disabled={loading || !task.trim()}
            className={clsx(
              "sm:w-24 py-3 sm:py-0 rounded-xl flex items-center justify-center gap-2 sm:flex-col sm:gap-1.5 text-xs font-bold transition-all duration-200",
              loading || !task.trim()
                ? "bg-nexus-border text-nexus-muted cursor-not-allowed"
                : "bg-gradient-to-br from-nexus-accent to-indigo-600 text-white hover:shadow-nexus-md hover:scale-[1.02] active:scale-[0.98]",
            )}
          >
            {loading ? (
              <Activity className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
            <span>{loading ? "Planning…" : "Run Task"}</span>
          </button>
        </div>

        {error && (
          <p className="text-nexus-rose text-xs font-mono bg-nexus-rose/10 border border-nexus-rose/20 rounded-lg px-3 py-2 animate-shake">
            ✗ {error}
          </p>
        )}

        {taskId && (
          <div className="flex items-center gap-3 text-nexus-cyan text-xs font-mono bg-nexus-cyan/10 border border-nexus-cyan/30 rounded-lg px-4 py-3 animate-pulse">
            <Activity className="w-4 h-4" />
            <div className="flex flex-col">
              <span className="font-bold uppercase tracking-widest text-[10px]">
                Active Mesh Execution
              </span>
              <span className="text-nexus-text">#{taskId}</span>
            </div>
          </div>
        )}
      </div>

      {/* Live Thought Stream */}
      {taskId && (
        <div className="animate-slide-up">
          <ThoughtStream taskId={taskId} />
        </div>
      )}

      {!taskId && recentTasks.length > 0 && (
        <div className="glass border-gradient rounded-2xl p-6 space-y-4 shadow-nexus-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-nexus-amber" />
              <h2 className="text-base font-semibold text-nexus-text">
                Recent Project Activity
              </h2>
            </div>
            <button
              onClick={() => {
                clearTasks().then(() => fetchStats());
              }}
              className="text-[10px] text-nexus-rose font-mono hover:underline uppercase tracking-widest"
            >
              Clear Logs
            </button>
          </div>

          <div className="space-y-2 overflow-hidden">
            {recentTasks.map((t) => (
              <div
                key={t.id}
                className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/5 hover:border-nexus-border/50 transition-all cursor-pointer group"
                onClick={() => setTaskId(t.id)}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={clsx(
                      "w-2 h-2 rounded-full",
                      t.status === "completed"
                        ? "bg-nexus-emerald"
                        : t.status === "error"
                        ? "bg-nexus-rose"
                        : "bg-nexus-amber animate-pulse",
                    )}
                  />
                  <div className="flex flex-col">
                    <span className="text-sm text-nexus-text font-medium line-clamp-1">
                      {t.task_text}
                    </span>
                    <span className="text-[10px] text-nexus-muted font-mono">
                      {new Date(t.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className={clsx(
                      "text-[10px] font-mono px-2 py-0.5 rounded-full border uppercase tracking-tighter",
                      t.status === "completed"
                        ? "bg-nexus-emerald/10 border-nexus-emerald/30 text-nexus-emerald"
                        : t.status === "error"
                        ? "bg-nexus-rose/10 border-nexus-rose/30 text-nexus-rose"
                        : "bg-nexus-amber/10 border-nexus-amber/30 text-nexus-amber",
                    )}
                  >
                    {t.status}
                  </span>
                  <div
                    onClick={(e) => {
                      e.stopPropagation();
                      if (confirm("Delete this task?")) {
                        import("@/lib/api")
                          .then((api) => api.deleteTask(t.id))
                          .then(() => fetchStats());
                      }
                    }}
                    className="p-1.5 rounded-lg hover:bg-nexus-rose/20 text-nexus-muted hover:text-nexus-rose transition-colors"
                  >
                    <Activity className="w-3.5 h-3.5 rotate-45" />{" "}
                    {/* Use Activity for trash-like feel if Trash2 not imported */}
                  </div>
                  <ArrowRight className="w-3 h-3 text-nexus-muted group-hover:text-nexus-text transition-colors" />
                </div>
              </div>
            ))}
          </div>

          {/* Activity Pagination */}
          <div className="flex items-center justify-between px-1 text-[10px] font-mono font-bold uppercase tracking-widest text-nexus-muted pt-2 border-t border-nexus-border/40">
            <span>Activity Page {currentPage}</span>
            <div className="flex gap-2">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setCurrentPage(Math.max(1, currentPage - 1));
                }}
                disabled={currentPage === 1}
                className="px-2 py-1 rounded border border-nexus-border hover:bg-white/5 transition-all disabled:opacity-20"
              >
                Prev
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setCurrentPage(currentPage + 1);
                }}
                disabled={recentTasks.length < 20}
                className="px-2 py-1 rounded border border-nexus-border hover:bg-white/5 transition-all disabled:opacity-20"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {!taskId && recentTasks.length === 0 && (
        <div className="glass border-gradient rounded-2xl p-10 flex flex-col items-center justify-center text-center opacity-40 border-dashed">
          <Clock className="w-12 h-12 mb-4 text-nexus-muted" />
          <h3 className="text-lg font-bold text-nexus-text">
            Waiting for Task
          </h3>
          <p className="text-sm text-nexus-muted max-w-sm">
            Launch a task above to witness the autonomous mesh in action. Full
            audit logs are available in the Governance segment.
          </p>
        </div>
      )}

      {/* Architecture Overview */}
      <div className="glass border-gradient rounded-2xl p-6 space-y-4 shadow-nexus-sm">
        <div className="flex items-center gap-2">
          <Layers className="w-4 h-4 text-nexus-cyan" />
          <h2 className="text-base font-semibold text-nexus-text">
            System Architecture
          </h2>
        </div>
        <div className="relative w-full overflow-hidden rounded-xl border border-nexus-border/50 bg-nexus-bg/30 p-2">
          <img
            src="/nexus_node_architecture.png"
            alt="NEXUS-NODE System Architecture"
            className="w-full h-auto rounded-lg shadow-2xl"
          />
          <div className="mt-4 flex items-center justify-between text-[10px] text-nexus-muted font-mono uppercase tracking-widest px-1">
            <span>High-Fidelity Action Mesh Visualization</span>
            <span>v1.0.0-Stable</span>
          </div>
        </div>
      </div>
    </div>
  );
}
