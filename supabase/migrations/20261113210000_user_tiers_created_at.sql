-- user_tiers.created_at: set when getEffectiveTier bootstraps the row on the
-- user's first dashboard load, so it measures first dashboard load, not Clerk signup.
alter table user_tiers add column if not exists created_at timestamptz not null default now();
