from enum import Enum
import asyncio


class OpState(Enum):
    RUN = 'RUNNING'
    PAUSE = 'PAUSED'
    CANCEL = 'CANCELED'


class OpControl:
    def __init__(self, dao):
        self.state = OpState.RUN
        self.dao = dao

    async def get_state(self, operation):
        op_data = await self.dao.get('opstate', dict(operation=operation))
        if len(op_data) > 0:
            return op_data[0].get('state')
        return ''

    async def check_status(self, operation):
        while True:
            state = await self.get_state(operation)
            if state == OpState.RUN.value or state == '':
                break
            elif state == OpState.CANCEL.value:
                return 'Cancel Requested'
            else:
                await asyncio.sleep(5)

    async def is_canceled(self, operation):
        state = await self.get_state(operation)
        if state == 'CANCELED':
            return True
        return False

    async def pause_operation(self, operation):
        if not await self.is_canceled(operation):
            await self.dao.delete('opstate', dict(operation=operation))
            await self.dao.create('opstate', dict(operation=operation,state=OpState.PAUSE.value))

    async def run_operation(self, operation):
        if not await self.is_canceled(operation):
            await self.dao.delete('opstate', dict(operation=operation))
            await self.dao.create('opstate', dict(operation=operation, state=OpState.RUN.value))

    async def cancel_operation(self, operation):
        await self.dao.delete('opstate', dict(operation=operation))
        await self.dao.create('opstate', dict(operation=operation, state=OpState.CANCEL.value))

    async def cleanup_operation(self, operation):
        await self.dao.delete('opstate', dict(operation=operation))

