import copy
import os
import shutil
import pickle
import tarfile

from datetime import datetime

import app.service.data_svc
from app.utility.base_service import BaseService

DATA_BACKUP_DIR = app.service.data_svc.DATA_BACKUP_DIR
FACT_STORE_PATH = "data/fact_store"

class BaseKnowledgeService(BaseService):

    def __init__(self):
        self.log = self.add_service('knowledge_svc', self)
        self.schema = dict(facts=[], relationships=[], rules=[])
        self.fact_ram = copy.deepcopy(self.schema)

    # -- Fact API --
    def _add_fact(self, fact):
        """facts can now be highly controlled, with visibility at the
        operation level, agent(s) level, or custom groupings"""
        if not any(x == fact for x in self.fact_ram['facts']):
            self.fact_ram['facts'].append(fact)

    def _update_fact(self, criteria, updates):
        matches = self._get_facts(criteria)
        for match in matches:
            for k, v in updates.items():
                if getattr(match, k, False):
                    setattr(match, k, v)

    def _get_facts(self, criteria):
        """Becomes a powerful function, because it sorts and filters out facts based on
        input (values, groupings) as well as underlying mechanisms such as fact mutexs"""
        return self._locate('facts', query=criteria)

    def _delete_fact(self, criteria):
        """Delete existing facts based on provided information"""
        return self._remove('facts', criteria)

    def _get_meta_facts(self, meta_fact=None, agent=None, group=None):
        """Returns the complete set of facts associated with a meta-fact construct"""
        raise NotImplemented

    def _get_fact_origin(self, fact):
        """Retrieve the specific origin of a fact. If it was learned in the current operation, parse through links to
        identify the host it was discovered on."""
        raise NotImplemented

    # -- Relationships API --

    def _get_relationships(self, criteria):
        return self._locate('relationships', query=criteria)

    def _add_relationship(self, relationship):
        if not any((x.source == relationship.source) and (x.edge == relationship.edge) and
                   (x.target == relationship.target) for x in self.fact_ram['relationships']):
            self.fact_ram['relationships'].append(relationship)

    def _update_relationship(self, criteria, updates):
        matches = self._get_relationships(criteria)
        for match in matches:
            for k, v in updates.items():
                if getattr(match, k, False):
                    setattr(match, k, v)

    def _delete_relationship(self, criteria):
        return self._remove('relationships', criteria)

    # --- Rule API ---

    def _add_rule(self, rule):
        """
        Args:
            rule.action: [DENY, ALLOW, EXCLUSIVE, EXCLUSIVE_TRAIT, EXCLUSIVE_VALUE], 'EXCLUSIVE_*' actions denote that
                the trait/value will be made mutually exclusive in its use to the agent/group/operation that is
                specified for. Essentially a fact is binded to mutex, and only one action can be using the fact
                at any one time.
        """
        if not any((x.action == rule.action) and (x.trait == rule.trait) for x in self.fact_ram['rules']):
            self.fact_ram['rules'].append(rule)

    def _get_rules(self, criteria):
        return [x for x in self.fact_ram['rules'] if self._check_rule(x, criteria, True)]

    def _delete_rule(self, criteria):
        """Remove an existing rule from the system"""
        self.fact_ram['rules'][:] = [x for x in self.fact_ram['rules'] if not self._check_rule(x, criteria)]
        return

    @staticmethod
    def _check_rule(rule, desired_quals, wildcard=False):
        criteria_matches = []
        for k, v in desired_quals.items():
            if getattr(rule, k) == v:
                criteria_matches.append(True)
            elif k == 'match' and wildcard:  # support wildcard matching
                val = getattr(rule, k)
                local_stub = val.split('*')
                input_stub = v.split('*')
                if all(x in v for x in local_stub) or all(x in val for x in input_stub):
                    criteria_matches.append(True)
        if len(criteria_matches) == len(desired_quals):
            return True

    # --- New Inferencing API ---
    # NOT IMPLEMENTED YET
    def _similar_facts(self, fact, agent, group):
        """return facts that are close to supplied fact.


        Ex:
            - other facts for an agent with given trait/value
            - other facts for the group/agent
            - other facts with same value
        """
        raise NotImplemented

    def _fact_value_distribution(self, critera, agent=None, group=None):
        """return the value distribution for the given fact, and further filtered down
        to agent/group if supplied


        Ex: fact value distribution for 'host.user.name' on group 'workstations':
            --> [{'admin': .4}, {'system': .4}, {'michael': .1}, {'workstation1': .1}]
        """
        raise NotImplemented

    def _best_guess(self, criteria, agent=None, group=None):
        """wrapper around 'fact_value_distribution', just returning highest probable value"""
        raise NotImplemented

    def _best_facts(self, agent=None, group=None, metric='usage_success'):
        """best facts based on requested metric


        Args:
            metric: ['usage_success', 'most_recent_success', ...]
        """
        raise NotImplemented

    def _locate(self, object_name, query=None):
        try:
            return [obj for obj in self.fact_ram[object_name] if obj.match(query)]
        except Exception as e:
            self.log.error('[!] LOCATE: %s' % e)

    def _remove(self, object_name, query):
        try:
            self.fact_ram[object_name][:] = [obj for obj in self.fact_ram[object_name] if not obj.match(query)]
        except Exception as e:
            self.log.error('[!] REMOVE: %s' % e)

    @staticmethod
    def _delete_file(path):
        if not os.path.exists(path):
            return
        elif os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

    @staticmethod
    def _destroy():
        """Reset the caldera data directory and server state.

        This creates a gzipped tarball backup of the data files tracked by caldera.
        Paths are preserved within the tarball, with all files having "data/" as the
        root.
        """
        if not os.path.exists(DATA_BACKUP_DIR):
            os.mkdir(DATA_BACKUP_DIR)

        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        tarball_path = os.path.join(DATA_BACKUP_DIR, f'backup-{timestamp}.tar.gz')

        with tarfile.open(tarball_path, 'w:gz') as tarball:
            tarball.add(FACT_STORE_PATH)
            BaseKnowledgeService._delete_file(FACT_STORE_PATH)

    async def _save_state(self):
        await self.get_service('file_svc').save_file('object_store', pickle.dumps(self.fact_ram), 'data')

    async def _restore_state(self):
        """
        Restore the object database

        :return:
        """
        if os.path.exists(FACT_STORE_PATH):
            _, store = await self.get_service('file_svc').read_file(FACT_STORE_PATH.split(os.path.sep)[1],
                                                                    FACT_STORE_PATH.split(os.path.sep)[0])
            # Pickle is only used to load a local file that caldera creates. Pickled data is not
            # received over the network.
            ram = pickle.loads(store)  # nosec
            for key in ram.keys():
                self.fact_ram[key] = []
                for c_object in ram[key]:
                    handle = self._load_wrapper(key)
                    handle(c_object)
            self.log.debug('Restored data from persistent storage')

    def _load_wrapper(self, key):
        if key == 'facts':
            return self._add_fact
        elif key == 'relationships':
            return self._add_relationship
        elif key == 'rules':
            return self._add_rule
