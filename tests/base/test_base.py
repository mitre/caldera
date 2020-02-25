import asyncio
import unittest

from app.service.app_svc import AppService
from app.service.data_svc import DataService
from app.service.learning_svc import LearningService
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService


class TestBase(unittest.TestCase):

    def initialize(self):
        self.app_svc = AppService(None)
        self.data_svc = DataService()
        self.rest_svc = RestService()
        self.planning_svc = PlanningService()
        self.learning_svc = LearningService()
        self.services = [self.app_svc.get_services()]

    @staticmethod
    def run_async(c):
        return asyncio.get_event_loop().run_until_complete(c)
