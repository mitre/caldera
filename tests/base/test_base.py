import os
from pathlib import Path

import yaml
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase

from app.api.rest_api import RestApi
from app.service.app_svc import AppService
from app.service.auth_svc import AuthService
from app.service.contact_svc import ContactService
from app.service.data_svc import DataService
from app.service.file_svc import FileSvc
from app.service.learning_svc import LearningService
from app.service.planning_svc import PlanningService
from app.service.rest_svc import RestService
from app.utility.base_world import BaseWorld


class TestBase(AioHTTPTestCase):

    @classmethod
    def patch_config(cls):
        with open(Path(__file__).parents[2] / 'conf' / 'default.yml', 'r') as fle:
            BaseWorld.apply_config('default', yaml.safe_load(fle))

    def initialize(self):
        self.patch_config()
        self.app_svc = AppService(web.Application())
        self.data_svc = DataService()
        self.rest_svc = RestService()
        self.planning_svc = PlanningService()
        self.learning_svc = LearningService()
        self.auth_svc = AuthService()
        self.contact_svc = ContactService()
        self.file_svc = FileSvc()
        self.services = self.app_svc.get_services()

    async def get_application(self):
        """
        Overrides AioHTTPTestCase.get_application to provide our TestCase with our server's application.
        """
        os.chdir(str(Path(__file__).parents[2]))
        self.initialize()
        await self.app_svc.register_contacts()
        await self.app_svc.load_plugins()
        self.rest_api = await RestApi(self.services).enable()
        await self.auth_svc.apply(self.app_svc.application, self.auth_svc.get_config('users'))
        return self.app_svc.application

    def run_async(self, c):
        return self.loop.run_until_complete(c)
