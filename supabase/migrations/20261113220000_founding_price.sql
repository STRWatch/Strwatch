-- True when the user's subscription was created through the founding-member
-- checkout ($19/mo locked). Set by the Stripe webhook from session metadata;
-- used by the admin MRR estimate.
alter table user_tiers add column if not exists founding_price boolean not null default false;
