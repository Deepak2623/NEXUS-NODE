"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  GitBranch,
  Home,
  Network,
  Shield,
  X,
  Zap,
} from "lucide-react";
import { clsx } from "clsx";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: Home },
  { href: "/mesh", label: "Live Mesh", icon: Network },
  { href: "/governance", label: "Governance", icon: Shield },
  { href: "/integrations", label: "Integrations", icon: GitBranch },
];

interface SidebarProps {
  onClose?: () => void;
}

export function Sidebar({ onClose }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="flex flex-col w-64 h-full glass-panel mr-4 lg:mr-0 z-50">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-nexus-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative shrink-0">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-nexus-accent to-nexus-cyan flex items-center justify-center shadow-nexus-md">
                <Zap className="w-5 h-5 text-white" />
              </div>
              <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-nexus-emerald rounded-full border-2 border-nexus-surface ping-slow" />
            </div>
            <div className="min-w-0">
              <h2 className="text-sm font-bold text-nexus-text tracking-wider truncate">
                NEXUS-NODE
              </h2>
              <p className="text-[10px] text-nexus-muted font-mono uppercase tracking-widest truncate">
                Action Mesh v0.1
              </p>
            </div>
          </div>
          {/* Close button — mobile only */}
          {onClose && (
            <button
              aria-label="Close navigation menu"
              onClick={onClose}
              className="lg:hidden p-1.5 rounded-lg text-nexus-muted hover:text-nexus-text hover:bg-white/5 transition-all shrink-0"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav
        className="flex-1 px-3 py-4 space-y-1 overflow-y-auto"
        aria-label="Main navigation"
      >
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              aria-label={label}
              onClick={onClose}
              className={clsx(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group",
                active
                  ? "bg-nexus-accent/20 text-nexus-accent-glow shadow-nexus-sm border border-nexus-accent/20"
                  : "text-nexus-muted hover:bg-white/5 hover:text-nexus-text border border-transparent",
              )}
            >
              <Icon
                className={clsx(
                  "w-4 h-4 shrink-0 transition-all",
                  active
                    ? "text-nexus-accent-glow"
                    : "group-hover:text-nexus-text",
                )}
              />
              <span className="truncate">{label}</span>
              {active && (
                <span className="ml-auto w-1.5 h-1.5 shrink-0 rounded-full bg-nexus-accent animate-pulse-slow" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Status footer */}
      <div className="px-4 py-4 border-t border-nexus-border">
        <div className="glass rounded-xl p-3 space-y-2">
          <p className="text-[10px] font-mono text-nexus-muted uppercase tracking-widest mb-2">
            System Status
          </p>
          {[
            { label: "Groq (node_plan)", color: "bg-nexus-emerald" },
            { label: "Gemini (node_verify)", color: "bg-nexus-emerald" },
            { label: "GovernorNode", color: "bg-nexus-emerald" },
          ].map(({ label, color }) => (
            <div key={label} className="flex items-center gap-2">
              <span
                className={clsx("w-1.5 h-1.5 shrink-0 rounded-full", color)}
              />
              <span className="text-[10px] text-nexus-text-dim truncate">
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </aside>
  );
}
