/** abilities **/
CREATE TABLE if not exists core_ability (id integer primary key AUTOINCREMENT, ability_id text, tactic text, technique_name, technique_id text, name text, test text, description text, cleanup text, executor, platform, UNIQUE (ability_id, platform, executor) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_payload (ability integer, payload text, UNIQUE (ability, payload) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_parser (id integer primary key AUTOINCREMENT, ability integer, module text, UNIQUE(ability, module) ON CONFLICT REPLACE);
CREATE TABLE if not exists core_parser_map (parser_id integer, source text, edge text, target text, UNIQUE(parser_id, source, edge, target) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_requirement (id integer primary key AUTOINCREMENT, ability integer, module text, UNIQUE(ability, module) ON CONFLICT REPLACE);
CREATE TABLE if not exists core_requirement_map (requirement_id integer, source text, edge text, target text, UNIQUE(requirement_id, source, edge, target) ON CONFLICT IGNORE);
/** planners **/
CREATE TABLE if not exists core_planner (id integer primary key AUTOINCREMENT, name text, module text, params json, UNIQUE(name) ON CONFLICT IGNORE);
/** adversaries **/
CREATE TABLE if not exists core_adversary (id integer primary key AUTOINCREMENT, adversary_id text, name text, description text, UNIQUE (adversary_id));
CREATE TABLE if not exists core_adversary_map (id integer primary key AUTOINCREMENT, phase integer, adversary_id text, ability_id text, UNIQUE (adversary_id, phase, ability_id));
/** facts **/
CREATE TABLE if not exists core_fact (id integer primary key AUTOINCREMENT, property text, value text, score integer, source_id text, link_id integer DEFAULT 0);
CREATE TABLE if not exists core_source (id integer primary key AUTOINCREMENT, name text, UNIQUE(name) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_source_map (id integer primary key AUTOINCREMENT, op_id integer, source_id integer, UNIQUE(op_id, source_id) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_rule (id integer primary key AUTOINCREMENT, action integer, fact text, match text, source_id text);
/** agents **/
CREATE TABLE if not exists core_agent (id integer primary key AUTOINCREMENT, paw text, last_seen date, architecture text, platform text, server text, host_group text, location text, pid integer, ppid integer, trusted integer, last_trusted_seen date, sleep_min integer, sleep_max integer);
CREATE TABLE if not exists core_executor (id integer primary key AUTOINCREMENT, agent_id integer, executor text, preferred integer, UNIQUE(agent_id, executor) ON CONFLICT REPLACE);
/** operations **/
CREATE TABLE if not exists core_operation (id integer primary key AUTOINCREMENT, name text, host_group text, adversary_id text, jitter text, start date, finish date, phase integer, autonomous integer, planner integer, state text, allow_untrusted integer);
CREATE TABLE if not exists core_chain (id integer primary key AUTOINCREMENT, op_id integer, paw text, ability integer, jitter integer, command text, executor text, cleanup integer, score integer, status integer, decide date, collect date, finish date, UNIQUE(op_id, paw, command));
CREATE TABLE if not exists core_used (id integer primary key AUTOINCREMENT, link_id integer, fact_id integer, UNIQUE(link_id, fact_id) ON CONFLICT IGNORE);
CREATE TABLE if not exists core_result (link_id integer, output text, parsed data);
CREATE TABLE if not exists core_relationship (link_id integer, source integer, edge text, target integer, UNIQUE(link_id, source, edge, target) ON CONFLICT IGNORE);
