from app.utility.base_world import BaseWorld

name = 'PluginA'
description = 'Test plugin'
address = None
access = BaseWorld.Access.RED

async def enable(services):
    x = 2+2