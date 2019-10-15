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
                matched_facts.append((dict(fact=parser['property'], value=entry.get(parser['script']))))
        elif isinstance(structured, (dict,)):
            dict_match = parser['script']
            dict_match = dict_match.split(',')
            match = structured
            for d in dict_match:
                match = match[d]
            matched_facts.append((dict(fact=parser['property'], value=match)))
        else:
            matched_facts.append((dict(fact=parser['property'], value=structured[parser['script']])))
    return matched_facts


def regex(parser, blob, **kwargs):
    matched_facts = []
    for i, v in enumerate([m for m in re.findall(parser['script'], blob.strip())]):
        matched_facts.append(dict(fact=parser['property'], value=v))
    return matched_facts


def line(parser, blob, **kwargs):
    return [dict(fact=parser['property'], value=f.strip()) for f in blob.split('\n') if f.strip()]

