import json
import re

PARSER_SIGNALS_FAILURE = 418  # Universal Teapot error code


class BaseParser:

    def __init__(self, parser_info):
        self.mappers = parser_info['mappers']
        self.used_facts = parser_info['used_facts']
        self.source_facts = parser_info['source_facts']

    @staticmethod
    def set_value(search, match, used_facts):
        """
        Determine the value of a source/target for a Relationship
        :param search: a fact property to look for; either a source or target fact
        :param match: a parsing match
        :param used_facts: a list of facts that were used in a command
        :return: either None, the value of a matched used_fact, or the parsing match
        """
        if not search:
            return None
        for uf in used_facts:
            if search == uf.trait:
                return uf.value
        return match

    @staticmethod
    def email(blob):
        """
        Parse out email addresses
        :param blob:
        :return:
        """
        return re.findall(r'[\w\.-]+@[\w\.-]+', blob)

    @staticmethod
    def filename(blob):
        """
        Parse out filenames
        :param blob:
        :return:
        """
        return re.findall(r'\b\w+\.\w+', blob)

    @staticmethod
    def line(blob):
        """
        Split a blob by line
        :param blob:
        :return:
        """
        return [x.rstrip('\r') for x in blob.split('\n') if x]

    @staticmethod
    def ip(blob):
        return re.findall(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', blob)

    @staticmethod
    def broadcastip(blob):
        return re.findall(r'(?<=broadcast ).*', blob)

    @staticmethod
    def load_json(blob):
        try:
            return json.loads(blob)
        except Exception:
            return None
