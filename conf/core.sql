CREATE TABLE if not exists core_result (link_id integer, output text, parsed data);
CREATE TABLE if not exists core_ability (id integer primary key AUTOINCREMENT, ability_id text, tactic text, technique_name, technique_id text, name text, test text, description text, cleanup text, executor, platform, UNIQUE (ability_id, platform, executor) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_payload (id integer primary key AUTOINCREMENT, ability integer, payload text, UNIQUE (ability, payload) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_adversary (id integer primary key AUTOINCREMENT, adversary_id text, name text, description text, UNIQUE (name));
CREATE TABLE if not exists core_adversary_map (phase integer, adversary_id text, ability_id text, UNIQUE (adversary_id, phase, ability_id));
<<<<<<< HEAD
CREATE TABLE if not exists core_agent (id integer primary key AUTOINCREMENT, paw text, last_seen date, architecture text, platform text, server text, host_group text, location text, pid integer, ppid integer);
CREATE TABLE if not exists core_executor (id integer primary key AUTOINCREMENT, agent_id integer, executor text, preferred integer);
CREATE TABLE if not exists core_operation (id integer primary key AUTOINCREMENT, name text, host_group text, adversary_id text, jitter text, start date, finish date, phase integer, stealth integer, planner integer, state text);
CREATE TABLE if not exists core_chain (id integer primary key AUTOINCREMENT, op_id integer, paw text, ability integer, jitter integer, command text, executor text, cleanup integer, score integer, status integer, decide date, collect date, finish date, UNIQUE(op_id, paw, command));
=======
CREATE TABLE if not exists core_agent (id integer primary key AUTOINCREMENT, paw text, last_seen date, platform text, executor text, server text, host_group text, location text, pid integer, ppid integer);
CREATE TABLE if not exists core_operation (id integer primary key AUTOINCREMENT, name text, host_group text, adversary_id text, jitter text, start date, finish date, phase integer, stealth integer, planner integer, state text, max_waiting integer);
CREATE TABLE if not exists core_compromised_agents_map (id integer primary key AUTOINCREMENT, op_id integer, agent_id integer, UNIQUE(op_id, agent_id) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_chain (id integer primary key AUTOINCREMENT, op_id integer, paw text, ability integer, jitter integer, command text, cleanup integer, score integer, status integer, decide date, collect date, finish date, UNIQUE(op_id, paw, command));
>>>>>>> cc404eaa47287172965bced8dd11380318323cda
CREATE TABLE if not exists core_parser (id integer primary key AUTOINCREMENT, ability integer, name text, property text, script text, UNIQUE(ability, property) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_fact (id integer primary key AUTOINCREMENT, property text, value text, score integer, set_id integer, source_id text, link_id integer);
CREATE TABLE if not exists core_source (id integer primary key AUTOINCREMENT, name text, UNIQUE(name) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_source_map (id integer primary key AUTOINCREMENT, op_id integer, source_id integer, UNIQUE(op_id, source_id) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_planner (id integer primary key AUTOINCREMENT, name text, module text, params json, UNIQUE(name) ON CONFLICT IGNORE);
