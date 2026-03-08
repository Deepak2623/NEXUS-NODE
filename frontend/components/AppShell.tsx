"use client";

import { useState } from "react";
import { Menu, X } from "lucide-react";
import { Sidebar } from "@/components/Sidebar";
import { clsx } from "clsx";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/60 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar — hidden on mobile, visible on lg+ */}
      <div
        className={clsx(
          "fixed inset-y-0 left-0 z-40 w-64 lg:static lg:translate-x-0 transition-transform duration-300 ease-in-out p-4 pr-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main content */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden lg:p-4 lg:pl-4">
        {/* Mobile top bar */}
        <header className="flex items-center gap-3 px-4 py-3 glass-panel rounded-none lg:hidden z-20">
          <button
            id="mobile-menu-btn"
            aria-label="Open navigation menu"
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg text-nexus-muted hover:text-nexus-text hover:bg-white/5 transition-all"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-nexus-accent to-nexus-cyan flex items-center justify-center">
              <span className="text-[10px] font-bold text-white">N</span>
            </div>
            <span className="text-sm font-bold text-nexus-text tracking-wider">
              NEXUS-NODE
            </span>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto glass-panel mt-4 lg:mt-0 lg:rounded-2xl rounded-t-2xl">
          {children}
        </main>
      </div>
    </div>
  );
}
