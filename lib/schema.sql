-- Dentist Fellowship Tracker — Supabase schema
-- Run this once in Supabase: Project > SQL Editor > New query > paste this whole file > Run.

create extension if not exists pgcrypto;

do $$ begin
    create type record_status as enum ('draft', 'confirmed');
exception
    when duplicate_object then null;
end $$;

do $$ begin
    create type appointment_status as enum ('scheduled', 'completed', 'cancelled', 'no_show');
exception
    when duplicate_object then null;
end $$;

create table if not exists patients (
    id uuid primary key default gen_random_uuid(),
    display_name text not null,
    age int,
    sex text,
    created_at timestamptz not null default now(),
    notes text
);

create table if not exists procedures (
    id uuid primary key default gen_random_uuid(),
    patient_id uuid not null references patients(id) on delete cascade,
    date date not null,
    procedure_type text not null,
    tooth text,
    description text,
    complications text,
    follow_up_needed boolean not null default false,
    follow_up_date date,
    status record_status not null default 'draft',
    raw_input text
);

create table if not exists appointments (
    id uuid primary key default gen_random_uuid(),
    patient_id uuid not null references patients(id) on delete cascade,
    datetime timestamptz not null,
    purpose text,
    status appointment_status not null default 'scheduled'
);

create table if not exists daily_logs (
    id uuid primary key default gen_random_uuid(),
    date date not null default current_date,
    raw_input text not null,
    parsed_summary text,
    linked_procedure_ids uuid[] not null default '{}',
    status record_status not null default 'draft'
);

create table if not exists report_snapshots (
    id uuid primary key default gen_random_uuid(),
    generated_at timestamptz not null default now(),
    period_start date not null,
    period_end date not null,
    content text,
    stats_json jsonb
);

create index if not exists idx_procedures_patient_id on procedures(patient_id);
create index if not exists idx_procedures_status on procedures(status);
create index if not exists idx_procedures_date on procedures(date);
create index if not exists idx_appointments_patient_id on appointments(patient_id);
create index if not exists idx_appointments_datetime on appointments(datetime);
create index if not exists idx_daily_logs_status on daily_logs(status);
create index if not exists idx_daily_logs_date on daily_logs(date);
