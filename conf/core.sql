CREATE TABLE if not exists core_result (link_id integer, output text, parsed data);
CREATE TABLE if not exists core_ability (id text, technique integer, name text, test text, description text, cleanup text, executor, UNIQUE (id, executor) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_group (id integer primary key AUTOINCREMENT, name text, UNIQUE(name));
CREATE TABLE if not exists core_group_map (group_id integer, agent_id integer, UNIQUE(group_id, agent_id));
CREATE TABLE if not exists core_adversary (id integer primary key AUTOINCREMENT, name text, description text, UNIQUE (name));
CREATE TABLE if not exists core_adversary_map (phase integer, adversary_id integer, ability_id text, UNIQUE (adversary_id, phase, ability_id));
CREATE TABLE if not exists core_operation (id integer primary key AUTOINCREMENT, name text, host_group integer, adversary integer, jitter text, start date, finish date, phase integer);
CREATE TABLE if not exists core_agent (id integer primary key AUTOINCREMENT, hostname text, paw text, checks integer, last_seen date, sleep integer, executor text, server text);
CREATE TABLE if not exists core_chain (id integer primary key AUTOINCREMENT, op_id integer, host_id integer, ability_id text, jitter integer, command text, score integer, status integer, decide date, collect date, finish date, UNIQUE(op_id, host_id, command));
CREATE TABLE if not exists core_parser (id integer primary key AUTOINCREMENT, ability_id text, name text, property text, script text, UNIQUE(ability_id, property) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_attack (attack_id text primary key, name text, tactic text, UNIQUE(attack_id));
CREATE TABLE if not exists core_cleanup (op_id integer, link_id integer, command text, ability_id text, agent_id integer, UNIQUE(link_id, command));
CREATE TABLE if not exists users (username text primary key, password blob, salt blob, last_login date);
CREATE TABLE if not exists webauth (ref_insert text primary key, passkey text, issued date);

ALTER TABLE core_operation ADD COLUMN stealth integer;
ALTER TABLE core_operation ADD COLUMN cleanup integer;
ALTER TABLE core_ability ADD COLUMN executor integer;
