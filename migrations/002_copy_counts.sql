alter table matuya_accounts
  add column email_copy_count integer not null default 0 check (email_copy_count >= 0);

alter table matuya_accounts
  add column password_copy_count integer not null default 0 check (password_copy_count >= 0);

alter table matuya_accounts
  add column last_email_copied_at text;

alter table matuya_accounts
  add column last_password_copied_at text;

update matuya_accounts
set email_copy_count = copy_count,
    last_email_copied_at = last_copied_at
where copy_count > 0;
