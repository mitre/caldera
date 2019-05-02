from enum import Enum
import asyncio

class OpState(Enum):
    RUN = "RUNNING"
    PAUSE = "PAUSED"
    CANCEL = "CANCELLED"

class OpControl:
    def __init__(self, dao):
        self.state = OpState.RUN
        self.dao = dao

    async def get_state(self, operation):
        op_data = await self.dao.get('opstate', dict(operation=operation))
        return op_data.get('state')

    async def check_status(self, operation):
        while True:
            state = self.get_state(operation)
            if state == OpState.RUN:
                break
            elif state == OpState.CANCEL:
                return "Cancel Requested"
            else:
                asyncio.sleep(5)

    async def pause_operation(self, operation):
        await self.dao.delete('opstate', dict(operation=operation))
        await self.dao.create('opstate', dict(operation=operation,state=OpState.PAUSE))

    async def run_operation(self, operation):
        await self.dao.delete('opstate', dict(operation=operation))
        await self.dao.create('opstate', dict(operation=operation, state=OpState.RUN))

    async def cancel_operation(self, operation):
        await self.dao.delete('opstate', dict(operation=operation))
        await self.dao.create('opstate', dict(operation=operation, state=OpState.CANCEL))

    async def cleanup_operation(self, operation):
        await self.dao.delete('opstate', dict(operation=operation))