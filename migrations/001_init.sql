create table if not exists schema_migrations (
  version text primary key,
  applied_at text not null
);

create table if not exists users (
  id integer primary key,
  username text not null unique,
  password_hash text not null,
  created_at text not null,
  updated_at text not null
);

create table if not exists matuya_accounts (
  id integer primary key,
  email text not null unique,
  password text not null,
  status text not null check (status in ('pending', 'running', 'success', 'failed')),
  error_message text,
  copy_count integer not null default 0 check (copy_count >= 0),
  last_copied_at text,
  created_by integer,
  started_at text,
  completed_at text,
  created_at text not null,
  updated_at text not null,
  foreign key (created_by) references users(id)
);

create index if not exists idx_matuya_accounts_status
  on matuya_accounts(status);

create index if not exists idx_matuya_accounts_created_at
  on matuya_accounts(created_at);

create index if not exists idx_matuya_accounts_created_by
  on matuya_accounts(created_by);
