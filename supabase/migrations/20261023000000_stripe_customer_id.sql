-- Stripe customer id on user_tiers. Introduced ad hoc on Oct 23 (commit cac110f5)
-- before supabase/migrations existed; recorded here so the schema is rebuildable.
-- Read/written by the Stripe webhook, portal, both crons, settings and admin.
alter table user_tiers add column if not exists stripe_customer_id text;
create index if not exists user_tiers_stripe_customer_id_idx on user_tiers (stripe_customer_id);
