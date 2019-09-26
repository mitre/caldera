import json as json_library
import re


def json(parser, blob, log):
    matched_facts = []
    if blob:
        try:
            structured = json_library.loads(blob)
        except:
            log.warning('Malformed json returned. Unable to retrieve any facts.')
            return matched_facts
        if isinstance(structured, (list,)):
            for i, entry in enumerate(structured):
                matched_facts.append((dict(fact=parser['property'], value=entry.get(parser['script']), set_id=i)))
        elif isinstance(structured, (dict,)):
            dict_match = parser['script']
            dict_match = dict_match.split(',')
            match = structured
            for d in dict_match:
                match = match[d]
            matched_facts.append((dict(fact=parser['property'], value=match, set_id=0)))
        else:
            matched_facts.append((dict(fact=parser['property'], value=structured[parser['script']], set_id=0)))
    return matched_facts


def regex(parser, blob, **kwargs):
    matched_facts = []
    for i, v in enumerate([m for m in re.findall(parser['script'], blob.strip())]):
        matched_facts.append(dict(fact=parser['property'], value=v, set_id=i))
    return matched_facts


def line(parser, blob, **kwargs):
    property_name = parser['property'][0]['property']
    return [dict(fact=property_name, value=f.strip(), set_id=0) for f in blob.split('\n') if f.strip()]


def testing(parser, blob, **kwargs):
    matched_facts=[]
    properties = parser['property']
    for j, line in enumerate(blob.split('\n')):
        for i, v in enumerate(line.split(',')):
            if v is not None and v is not '':
                matched_facts.append(dict(fact=properties[i]['property'], value=v, set_id=j))
    return matched_facts