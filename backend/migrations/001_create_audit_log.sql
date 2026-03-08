-- Migration: 001_create_audit_log
-- Supabase SQL editor — run once against your project

-- 1. Create the audit_log table
CREATE TABLE IF NOT EXISTS public.audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    task_id         TEXT NOT NULL,
    node            TEXT NOT NULL,
    actor           TEXT NOT NULL DEFAULT 'system',
    input_hash      TEXT NOT NULL,
    output_hash     TEXT,
    pii_flags       TEXT[] DEFAULT '{}',
    hitl_event      BOOLEAN NOT NULL DEFAULT FALSE,
    hitl_action     TEXT,                          -- 'approve' | 'reject' | NULL
    iteration       INTEGER DEFAULT 0
);

-- 2. Index for fast task lookups and pagination
CREATE INDEX IF NOT EXISTS idx_audit_log_task_id   ON public.audit_log (task_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON public.audit_log (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_node       ON public.audit_log (node);

-- 3. Create the tasks table (replaces in-memory dict)
CREATE TABLE IF NOT EXISTS public.tasks (
    id          TEXT PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    status      TEXT NOT NULL DEFAULT 'pending',   -- pending | running | completed | error | hitl_wait
    task_text   TEXT NOT NULL,
    actor       TEXT NOT NULL DEFAULT 'user',
    result      JSONB,
    error       TEXT,
    iteration   INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tasks_status     ON public.tasks (status);
CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON public.tasks (created_at DESC);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER tasks_updated_at
    BEFORE UPDATE ON public.tasks
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- 4. Row Level Security
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks     ENABLE ROW LEVEL SECURITY;

-- audit_log: service role can INSERT only — no UPDATE, no DELETE
-- Authenticated can SELECT (for the UI)
CREATE POLICY "service_insert_audit_log"
    ON public.audit_log FOR INSERT
    TO service_role
    WITH CHECK (true);

CREATE POLICY "authenticated_read_audit_log"
    ON public.audit_log FOR SELECT
    TO authenticated
    USING (true);

-- tasks: service role can do everything, authenticated can read
CREATE POLICY "service_all_tasks"
    ON public.tasks FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "authenticated_read_tasks"
    ON public.tasks FOR SELECT
    TO authenticated
    USING (true);

-- 5. Grant minimal privileges
GRANT SELECT ON public.audit_log TO authenticated;
GRANT SELECT ON public.tasks     TO authenticated;
GRANT INSERT ON public.audit_log TO service_role;
GRANT ALL    ON public.tasks     TO service_role;
