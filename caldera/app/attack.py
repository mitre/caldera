import requests
from .engine.objects import AttackTactic, AttackTechnique, AttackList, AttackGroup
import json
import re
from .util import grab_site


attack_url = 'https://attack.mitre.org'

def refresh_attack():
    params = dict(action='ask', format='json', query="[[Category:Tactic]]")
    tactic_results = grab_site("{}/{}".format(attack_url, 'api.php'), params=params, stream=False, mode='attack').json()
    tactics = {}
    for page, result in tactic_results['query']['results'].items():
        name = result['fulltext']
        tactic = AttackTactic.objects(name=name).first()
        if tactic is None:
            tactic = AttackTactic(name=name)
        tactic.url = result['fullurl']
        tactic.save()
        tactics[tactic.name] = tactic
    params['query'] = ("[[Category:Technique]]|?Has tactic|?Has ID|?Has display name|?Has technical "
                      "description|?Has platform|limit=9999")
    technique_results = grab_site("{}/{}".format(attack_url, 'api.php'), params=params, stream=False,
                                  mode='attack').json()
    for page, result in technique_results['query']['results'].items():
        technique_id = result['printouts']['Has ID'][0]
        technique = AttackTechnique.objects(technique_id=technique_id).first()
        if technique is None:
            technique = AttackTechnique(technique_id=technique_id)
        technique.name = result['printouts']['Has display name'][0]
        technique.url = result['fullurl']
        technique.tactics = [tactics[_['fulltext']]for _ in result['printouts']['Has tactic']]
        technique.description = result['printouts']['Has technical description'][0]
        for entry in result['printouts']['Has platform']:
            if 'Windows' in entry:
                technique.isWindows = True
            if 'Linux' in entry:
                technique.isLinux = True
            if 'MacOS' in entry or 'OS X' in entry:
                technique.isMac = True
        technique.save()
    ordered_list_raw = grab_site("{}/wiki/Template:Ordered_Tactics".format(attack_url), params=None, stream=False,
                                 mode='attack')
    extract_s1 = re.search('</div><p>[^<]*', str(ordered_list_raw.content), re.M | re.I)
    extract_s2 = extract_s1.group()[9:-2]
    listing = AttackList.objects().first()
    if listing is None:
        listing = AttackTechnique.objects()
    listing.master_list = extract_s2
    listing.save()
    params['query'] = ("[[Category:Group]]|?Has ID|?Has technique|?Has alias|limit=9999")
    group_results = grab_site("{}/{}".format(attack_url, 'api.php'), params=params, stream=False,
                                  mode='attack').json()
    for page, result in group_results['query']['results'].items():
        group_id = result['printouts']['Has ID'][0]
        group = AttackGroup.objects(group_id=group_id).first()
        if group is None:
            group = AttackGroup(group_id=group_id)
        group.url = result['fullurl']
        group.name = result['printouts']['Has alias'][0]
        tech_list= []
        for entry in result['printouts']['Has technique']:
            technique = AttackTechnique.objects(technique_id=entry['fulltext'][-5:]).first()
            tech_list.append(technique)
        group.techniques = tech_list
        group.aliases = result['printouts']['Has alias'][1:]
        group.save()

def load_default(attack_data=None):
    """Loads the default attack data into the database
    """
    attack_dumped = json.loads(attack_data)
    tactic_name_to_id = {}
    for tactic in attack_dumped['tactics']:
        saved = AttackTactic(name=tactic['name'], url=tactic['url']).save()
        tactic_name_to_id[tactic['name']] = saved.id

    for technique in attack_dumped['techniques']:
        tactic_ids = [tactic_name_to_id[x] for x in technique['tactics']]
        AttackTechnique(name=technique['name'], url=technique['url'], description=technique['description'],
                        technique_id=technique['technique_id'], tactics=tactic_ids, isLinux=technique['isLinux'],
                        isMac=technique['isMac'], isWindows=technique['isWindows']).save()
    listing = AttackList(master_list=attack_dumped['order'][0]['master_list'])
    listing.save()
    for group in attack_dumped['groups']:
        tech = []
        aliases = []
        for entry in group['techniques']:
            for db_tech in AttackTechnique.objects:
                if entry == db_tech.technique_id:
                    tech.append(db_tech)
        for entry in group['aliases']:
                     aliases.append(entry)
        AttackGroup(name=group['name'], group_id=group['group_id'], url=group['url'], aliases=aliases,
                    techniques=tech).save()
