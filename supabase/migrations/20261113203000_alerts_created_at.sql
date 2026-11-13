-- alerts.created_at: insertion time, independent of sent_at (which is NULL
-- for free-tier rows until the weekly digest goes out). The dashboard sorts
-- on this column; that app change is separate.
alter table alerts add column if not exists created_at timestamptz not null default now();

-- The free-tier digest queue stores rows with sent_at NULL until the weekly send.
alter table alerts alter column sent_at drop not null;

-- Backfill: rows that predate this column were inserted at send time.
update alerts set created_at = sent_at where sent_at is not null;
