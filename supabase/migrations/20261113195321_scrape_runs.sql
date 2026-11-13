-- scrape_runs: one row per scraper/source per run.py invocation.
-- Written by scraper/run.py with the service-role key; read by ops/admin.
create table if not exists scrape_runs (
  id bigserial primary key,
  source text not null,
  city text,
  started_at timestamptz not null,
  finished_at timestamptz,
  status text not null check (status in ('ok', 'changed', 'error')),
  pages_changed int default 0,
  error text
);

create index if not exists scrape_runs_source_started_at_idx
  on scrape_runs (source, started_at desc);

-- Service role (the scraper) bypasses RLS; nothing else reads this table.
alter table scrape_runs enable row level security;
