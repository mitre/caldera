import abc
from abc import ABC


class C2Active(ABC):

    @abc.abstractmethod
    def get_config(self):
        """
        Returns C2 config information to be encoded into agent
        :return: config information
        """
        return

    @abc.abstractmethod
    async def get_results(self):
        """
        Retrieve all results posted to this C2 channel
        :return: results
        """
        return

    @abc.abstractmethod
    async def get_beacons(self):
        """
        Retrieve all beacons posted to this C2 channel
        :return: the beacons
        """
        return

    @abc.abstractmethod
    async def post_payloads(self, payloads, paw):
        """
        Given a list of payloads and an agent paw, posts the payload to the c2 channel
        :param payloads:
        :param paw:
        :return:
        """
        return

    @abc.abstractmethod
    async def post_instructions(self, text, paw):
        """
        Post an instruction for the agent to execute
        :param text: The instruction text for the agent to execute
        :param paw: The paw for the agent to execute
        :return:
        """
        return
