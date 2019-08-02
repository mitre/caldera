from app.core.adversary import Adversary


class Operation:
    def __init__(self, name, host_group, adversary, planner, facts):
        self.id = None
        self.name = name
        self.host_group = host_group
        self.adversary = adversary
        self.planner = planner
        self.facts = facts or []

    @classmethod
    def from_data_svc(cls, operation):
        """
        :param operation: from calling data_svc await self.data_svc.explode_operation(dict(id=op_id))
        :return: Operation
        """
        return cls(name=operation[0]['name'],
                   host_group=operation[0]['host_group'],
                   adversary=Adversary(**operation[0]['adversary']),
                   planner=operation[0]['planner'],
                   facts=operation[0]['facts'])
