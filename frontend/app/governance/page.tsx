"use client";
import { useEffect, useState, useCallback } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  History as HistoryIcon,
  RefreshCw,
  Activity,
  Hash,
  Shield,
  UserCheck,
  Trash2,
  ExternalLink,
  X,
} from "lucide-react";
import { clsx } from "clsx";
import {
  approveHITL,
  getAuditLog,
  rejectHITL,
  getTasks,
  deleteTask,
  clearTasks,
} from "@/lib/api";

interface AuditEntry {
  id: string;
  created_at: string;
  task_id: string;
  node: string;
  actor: string;
  input_hash: string;
  output_hash: string;
  pii_flags: string[];
  hitl_event: boolean;
}

interface Toast {
  id: number;
  message: string;
  type: "success" | "error";
}

export default function GovernancePage() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = (message: string, type: "success" | "error" = "success") => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(
      () => setToasts((prev) => prev.filter((t) => t.id !== id)),
      3500,
    );
  };

  const fetchEverything = useCallback(
    async (showLoading = true) => {
      if (showLoading) setLoading(true);
      try {
        const [auditRes, tasksRes] = await Promise.all([
          getAuditLog(page, 50).catch(() => ({ entries: [] })),
          getTasks(50).catch(() => ({ tasks: [], count: 0 })),
        ]);

        setEntries((auditRes as any).entries ?? []);
        setTasks((tasksRes as any).tasks ?? []);
      } catch (err) {
        console.error("Governance fetch failed", err);
      } finally {
        if (showLoading) setLoading(false);
      }
    },
    [page],
  );

  useEffect(() => {
    fetchEverything(true);
    // Real-time update every 3 seconds
    const interval = setInterval(() => fetchEverything(false), 3000);
    return () => clearInterval(interval);
  }, [fetchEverything]);

  async function handleHITL(taskId: string, action: "approve" | "reject") {
    try {
      if (action === "approve") await approveHITL(taskId);
      else await rejectHITL(taskId);
      await fetchEverything(false);
    } catch (err) {
      console.error("HITL action failed", err);
    }
  }

  async function handleDeleteTask(id: string) {
    try {
      await deleteTask(id);
      await fetchEverything(false);
      addToast("Task deleted successfully", "success");
    } catch (err) {
      console.error("Delete task failed", err);
      addToast("Failed to delete task — check console", "error");
    }
  }

  async function handleClearAll() {
    if (
      !confirm(
        "Are you sure you want to permanently delete all task history and audit logs?",
      )
    )
      return;
    try {
      await clearTasks();
      await fetchEverything(false);
      addToast("All task history purged", "success");
    } catch (err) {
      console.error("Clear all failed", err);
      addToast("Failed to purge — check console", "error");
    }
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 space-y-8 animate-fade-in max-w-7xl mx-auto">
      {/* Toast Notifications */}
      <div className="fixed top-5 right-5 z-50 flex flex-col gap-2 pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={clsx(
              "flex items-center gap-3 px-4 py-3 rounded-xl border text-sm font-semibold shadow-nexus-md animate-slide-up pointer-events-auto",
              toast.type === "success"
                ? "bg-nexus-emerald/20 border-nexus-emerald/40 text-nexus-emerald"
                : "bg-nexus-rose/20 border-nexus-rose/40 text-nexus-rose",
            )}
          >
            {toast.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            )}
            {toast.message}
          </div>
        ))}
      </div>

      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-nexus-muted text-xs font-mono uppercase tracking-widest">
            <Shield className="w-4 h-4" />
            <span>Governance Hub</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-nexus-text text-glow-indigo">
            Audit & Compliance Control
          </h1>
          <p className="text-nexus-text-dim text-sm">
            Zero-trust chain of custody · SHA-256 integrity proofs · PII
            scrubbing active.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => fetchEverything(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold border border-nexus-border text-nexus-text hover:bg-white/5 transition-all shadow-nexus-sm"
          >
            <RefreshCw
              className={clsx("w-3.5 h-3.5", loading && "animate-spin")}
            />
            Sync Now
          </button>
          <button
            onClick={handleClearAll}
            className="flex items-center gap-2 px-4 py-2 rounded-xl bg-nexus-rose/10 border border-nexus-rose/20 text-nexus-rose hover:bg-nexus-rose/25 transition-all text-xs font-bold"
          >
            <Trash2 className="w-3.5 h-3.5" /> Purge History
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        {[
          {
            label: "Total Operations",
            value: String(entries.length),
            icon: Hash,
            color: "text-nexus-accent",
          },
          {
            label: "Tasks Executed",
            value: String(tasks.length),
            icon: HistoryIcon,
            color: "text-nexus-cyan",
          },
          {
            label: "PII Scrub Events",
            value: String(
              entries.filter((e) => e.pii_flags?.length > 0).length,
            ),
            icon: AlertTriangle,
            color: "text-nexus-amber",
          },
          {
            label: "HITL Interventions",
            value: String(entries.filter((e) => e.hitl_event).length),
            icon: Shield,
            color: "text-nexus-emerald",
          },
        ].map(({ label, value, icon: Icon, color }) => (
          <div
            key={label}
            className="glass border-gradient rounded-2xl p-5 hover:shadow-nexus-md transition-all"
          >
            <Icon className={clsx("w-5 h-5 mb-3", color)} />
            <p className={clsx("text-2xl font-bold", color)}>{value}</p>
            <p className="text-nexus-muted text-[10px] uppercase tracking-wider mt-1">
              {label}
            </p>
          </div>
        ))}
      </div>

      {/* Task History Section */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 px-1">
          <HistoryIcon className="w-4 h-4 text-nexus-cyan" />
          <h2 className="text-lg font-bold text-nexus-text">
            Task Execution History
          </h2>
          <span className="ml-auto text-[10px] font-mono text-nexus-muted bg-nexus-cyan/5 border border-nexus-cyan/20 px-2 py-0.5 rounded">
            Real-time Auto-refresh
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {tasks.length === 0 ? (
            <div className="lg:col-span-2 glass rounded-2xl p-12 text-center opacity-40">
              <Clock className="w-8 h-8 mx-auto mb-2 text-nexus-muted" />
              <p className="text-sm font-mono tracking-tight">
                No task history found.
              </p>
            </div>
          ) : (
            tasks.slice(0, 10).map((task) => (
              <div
                key={task.id}
                className="glass border-gradient rounded-2xl p-4 flex flex-col gap-3 group relative overflow-hidden"
              >
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-2">
                    <span
                      className={clsx(
                        "text-[9px] font-mono px-2 py-0.5 rounded uppercase font-bold border",
                        task.status === "completed"
                          ? "bg-nexus-emerald/10 border-nexus-emerald/30 text-nexus-emerald"
                          : task.status === "error" || task.status === "failed"
                          ? "bg-nexus-rose/10 border-nexus-rose/30 text-nexus-rose"
                          : task.status === "hitl_wait"
                          ? "bg-nexus-amber/10 border-nexus-amber/30 text-nexus-amber animate-pulse"
                          : "bg-nexus-cyan/10 border-nexus-cyan/30 text-nexus-cyan animate-pulse",
                      )}
                    >
                      {task.status}
                    </span>
                    <span className="text-[10px] font-mono text-nexus-muted">
                      #{task.id.slice(0, 8)}
                    </span>
                  </div>
                  <span className="text-[10px] text-nexus-muted font-mono">
                    {new Date(task.created_at).toLocaleString([], {
                      dateStyle: "short",
                      timeStyle: "short",
                    })}
                  </span>
                </div>
                <p className="text-sm text-nexus-text font-medium leading-relaxed pr-8">
                  {task.task_text}
                </p>
                <div className="flex items-center gap-4 mt-auto pt-2 border-t border-nexus-border/40">
                  <div className="flex items-center gap-1.5 text-[10px] text-nexus-muted font-mono">
                    <UserCheck className="w-3 h-3" /> {task.actor}
                  </div>
                  {task.iteration > 0 && (
                    <div className="flex items-center gap-1.5 text-[10px] text-nexus-muted font-mono">
                      <Activity className="w-3 h-3" /> {task.iteration}{" "}
                      iterations
                    </div>
                  )}
                  <a
                    href={`/?taskId=${task.id}`}
                    className="ml-auto text-[10px] text-nexus-accent hover:brightness-125 flex items-center gap-1 font-bold"
                  >
                    Re-Inspect <ExternalLink className="w-2.5 h-2.5" />
                  </a>
                </div>

                {/* Direct Action Buttons for HITL */}
                {task.status === "hitl_wait" && (
                  <div className="mt-3 flex gap-2 p-3 rounded-xl bg-nexus-amber/5 border border-nexus-amber/20 animate-slide-up">
                    <button
                      onClick={() => handleHITL(task.id, "approve")}
                      className="flex-1 py-2 rounded-lg bg-nexus-emerald text-nexus-bg text-xs font-bold hover:brightness-110 transition-all shadow-nexus-sm"
                    >
                      Approve Action
                    </button>
                    <button
                      onClick={() => handleHITL(task.id, "reject")}
                      className="flex-1 py-2 rounded-lg border border-nexus-rose/30 text-nexus-rose text-xs font-bold hover:bg-nexus-rose/10 transition-all"
                    >
                      Deny Access
                    </button>
                  </div>
                )}
                <button
                  onClick={() => handleDeleteTask(task.id)}
                  className="absolute top-4 right-4 p-2 rounded-lg text-nexus-rose bg-nexus-rose/5 border border-transparent hover:border-nexus-rose/30 opacity-0 group-hover:opacity-100 transition-all shadow-nexus-sm"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 px-1">
          <Shield className="w-4 h-4 text-nexus-emerald" />
          <h2 className="text-lg font-bold text-nexus-text">
            Atomic Audit Chain
          </h2>
        </div>

        <div className="glass rounded-2xl overflow-hidden border border-nexus-border shadow-nexus-md">
          <div className="overflow-x-auto">
            <table className="w-full text-[11px] min-w-[900px]">
              <thead>
                <tr className="border-b border-nexus-border bg-white/[0.04]">
                  {[
                    "Timestamp",
                    "Actor",
                    "Node",
                    "Action Target",
                    "Integrity Hash (SHA-256)",
                    "Status",
                    "Actions",
                  ].map((h) => (
                    <th
                      key={h}
                      className="px-5 py-3.5 text-left text-nexus-muted font-mono uppercase tracking-wider"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {entries.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="px-5 py-12 text-center text-nexus-muted font-mono opacity-50 italic"
                    >
                      No atomic entries recorded in the chain.
                    </td>
                  </tr>
                ) : (
                  entries.map((entry) => (
                    <tr
                      key={entry.id}
                      className="border-b border-nexus-border/30 hover:bg-white/[0.02] transition-colors"
                    >
                      <td className="px-5 py-4 font-mono text-nexus-muted whitespace-nowrap">
                        {new Date(entry.created_at).toLocaleTimeString(
                          "en-GB",
                          { hour12: false },
                        )}
                      </td>
                      <td className="px-5 py-4 font-bold text-nexus-text flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-nexus-emerald animate-pulse" />
                        {entry.actor}
                      </td>
                      <td className="px-5 py-4">
                        <span className="px-2 py-1 rounded bg-nexus-accent/10 border border-nexus-accent/20 text-nexus-accent-glow font-mono font-bold">
                          {entry.node}
                        </span>
                      </td>
                      <td className="px-5 py-4 font-mono text-nexus-text-dim">
                        {entry.task_id?.slice(0, 12)}...
                      </td>
                      <td className="px-5 py-4">
                        <div className="flex flex-col gap-0.5">
                          <span className="text-nexus-cyan font-mono text-[9px] truncate max-w-[120px]">
                            {entry.input_hash}
                          </span>
                          <span className="text-[8px] text-nexus-muted uppercase tracking-tighter">
                            Verified Integrity Proof
                          </span>
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        {entry.hitl_event ? (
                          <span className="flex items-center gap-1.5 text-nexus-amber font-bold">
                            <Clock className="w-3 h-3" /> PENDING HITL
                          </span>
                        ) : (
                          <span className="flex items-center gap-1.5 text-nexus-emerald font-bold">
                            <CheckCircle2 className="w-3 h-3" /> VERIFIED
                          </span>
                        )}
                      </td>
                      <td className="px-5 py-4">
                        {entry.hitl_event && (
                          <div className="flex gap-2">
                            <button
                              onClick={() =>
                                handleHITL(entry.task_id, "approve")
                              }
                              className="px-3 py-1.5 rounded-lg bg-nexus-emerald/10 border border-nexus-emerald/30 text-nexus-emerald hover:bg-nexus-emerald/20 transition-all font-bold text-[10px]"
                            >
                              Approve
                            </button>
                            <button
                              onClick={() =>
                                handleHITL(entry.task_id, "reject")
                              }
                              className="px-3 py-1.5 rounded-lg bg-nexus-rose/10 border border-nexus-rose/30 text-nexus-rose hover:bg-nexus-rose/20 transition-all font-bold text-[10px]"
                            >
                              Reject
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {/* Pagination Controls */}
          <div className="flex items-center justify-between px-5 py-4 bg-white/[0.02] border-t border-nexus-border">
            <p className="text-[10px] text-nexus-muted font-mono uppercase tracking-widest">
              Showing Page {page}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-4 py-2 rounded-xl text-[10px] font-bold border border-nexus-border text-nexus-text hover:bg-white/5 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={entries.length < 50}
                className="px-4 py-2 rounded-xl text-[10px] font-bold border border-nexus-border text-nexus-text hover:bg-white/5 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
