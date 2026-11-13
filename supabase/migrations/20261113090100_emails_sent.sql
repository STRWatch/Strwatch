create table if not exists emails_sent (
  id bigserial primary key,
  user_id text not null,
  template text not null,
  sent_at timestamptz default now(),
  unique (user_id, template)
);

-- Service-role only (the app uses the service key); no policies, so anon/authenticated get nothing.
alter table emails_sent enable row level security;
