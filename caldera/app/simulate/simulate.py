import inspect
from collections import defaultdict, OrderedDict
from caldera.app.cddl.build_ast import get_ast
from caldera.app.cddl.ast import StatementNode, ExprNode, DefineNode, IfNode, IfElNode, ForNode, CreateNode, KnowNode, \
    ForgetNode, PassNode, ParenNode, NotNode, ExistNode, CompNode, BinCompNode, ObjNode
from caldera.app.util import CaseException
from caldera.app.simulate.world import World, MetaWorld


class Simulator(object):
    def __init__(self, metaworld: MetaWorld, schema):
        self.meta_world = metaworld
        self.schema = schema
        self.agents = {}
        self.agent_done = {}
        self.log = []

    def register_agent(self, name, agent, world):
        self.agents[name] = (agent, world)
        self.agent_done[name] = False

    def tick(self, ticks):
        """Performs a tick in the simulation"""
        for agent_name in self.agents:
            agent, agent_world = self.agents[agent_name]
            # allow the agent to make a move
            self.agent_done[agent_name] = self._tick_agent(ticks, agent, agent_name, agent_world, self.meta_world, self.schema, self.log)

    @classmethod
    def _tick_agent(cls, ticks, agent, agent_name, agent_world: World, meta_world: MetaWorld, schema, log):
        """Perform a tick for a single agent"""
        agent.undefine_all_objects()

        for obj in agent_world.get_all_objects():
            obj_copy = obj.to_dict()
            del obj_copy['id']
            agent.define_object(obj.typ, obj['id'], obj_copy)

        # allow the agent to perform an action
        step, bindings, done_cb = agent.perform_best_step(3, 0)

        if not step or not bindings or not done_cb:
            return True

        # remap bindings to objects
        bindings = {k: agent_world.get_object_by_id(v) for k, v in bindings.items()}

        # map bindings into objects in the real world
        bindings = {k: meta_world.translate_object_to_real_world(v) for k, v in bindings.items()}

        sig = inspect.signature(step.description)
        description_args = {k: v for k, v in bindings.items() if k in sig.parameters}
        description = step.description(**description_args)

        print('Step #{}: "{}" is {}'.format(ticks, agent_name, description))

        # todo throw errors if the objects don't exist?

        # attempt to perform the action in the world
        success = cls.perform_action(step, bindings, meta_world, agent_world, schema)

        # notify the agent of success or failure
        if success:
            done_cb()

        log.append((agent, step, bindings, description, success))

        return False

    @classmethod
    def perform_action(cls, step, bindings, meta_world: MetaWorld, agent_world: World, schema) -> bool:
        # parse the cddl
        cddl_ast = get_ast(step.cddl, schema)
        try:
            cddl = cddl_ast[0]
        except IndexError:
            raise Exception("There was a problem parsing the cddl for step {}".format(step.display_name))

        # match the knowns with the bindings
        for stmt in cddl.effects:
            cls.execute_statement(bindings, meta_world, agent_world, stmt)

        # apply the bindings and rules to the current world and the agent's world

        return True

    @classmethod
    def evaluate_expression(cls, bindings, meta_world: MetaWorld, agent_world: World, expr: ExprNode):
        if isinstance(expr, ParenNode):
            raise Exception
        elif isinstance(expr, NotNode):
            raise Exception
        elif isinstance(expr, ExistNode):
            raise Exception
        elif isinstance(expr, CompNode):
            if expr.comp == 'in':
                left = cls.evaluate_expression(bindings, meta_world, agent_world, expr.left)
                right = cls.evaluate_expression(bindings, meta_world, agent_world, expr.right)
                return left in right
            elif expr.comp == '==':
                left = cls.evaluate_expression(bindings, meta_world, agent_world, expr.left)
                right = cls.evaluate_expression(bindings, meta_world, agent_world, expr.right)
                return left == right
            else:
                raise CaseException
        elif isinstance(expr, BinCompNode):
            left = cls.evaluate_expression(bindings, meta_world, agent_world, expr.left)
            if expr.comp == 'and':
                if not left:
                    return False
                return cls.evaluate_expression(bindings, meta_world, agent_world, expr.right)
            elif expr.comp == 'or':
                if left:
                    return True
                else:
                    return cls.evaluate_expression(bindings, meta_world, agent_world, expr.right)

            raise CaseException
        elif isinstance(expr, ObjNode):
            obj = None
            for item in expr.obj.split('.'):
                if not obj:
                    obj = bindings[item]
                else:
                    obj = obj[item]
            return obj
        elif isinstance(expr, str):
            return expr[1:-1]
        elif isinstance(expr, bool):
            return expr
        else:
            raise CaseException

    @classmethod
    def execute_statement(cls, bindings, meta_world: MetaWorld, agent_world: World, stmt: StatementNode):
        """Execute the statement within the world and the agent world"""
        if isinstance(stmt, DefineNode):
            # doesn't make sense in this context
            pass
        elif isinstance(stmt, IfNode):
            if cls.evaluate_expression(bindings, meta_world, agent_world, stmt.expr):
                for sub_stmt in stmt.stmts:
                    cls.execute_statement(bindings, meta_world, agent_world, sub_stmt)
        elif isinstance(stmt, IfElNode):
            pass
        elif isinstance(stmt, ForNode):
            # get each item in the obj
            for obj in cls.evaluate_expression(bindings, meta_world, agent_world, ObjNode(stmt.obj)):
                bindings[stmt.ident] = obj
                for sub_stmt in stmt.stmts:
                    cls.execute_statement(bindings, meta_world, agent_world, sub_stmt)
                del bindings[stmt.ident]
        elif isinstance(stmt, CreateNode):
            # make a node in
            obj_dict = {}
            for field_name, field_expr in stmt.field_values:
                obj_dict[field_name] = cls.evaluate_expression(bindings, meta_world, agent_world, field_expr)
            meta_world.create(agent_world, stmt.ident, obj_dict)
        elif isinstance(stmt, KnowNode):
            objects = OrderedDict()
            objects_properties = defaultdict(list)
            for item in stmt.obj:
                if len(item) == 1:
                    # this is the first node, look it up in the bindings
                    obj = bindings[item[0]]
                    # make sure this is the real world version of the object and not the agent version
                    assert obj.get_world() == meta_world.get_real_world()
                    objects[tuple(item)] = [obj]
                else:
                    child = item[-1]
                    parent = item[:-1]

                    # get the object representing the parent
                    if tuple(parent) not in objects:
                        parent_parent_objects = objects[tuple(parent[:-1])]
                        parent_objects = []
                        for parent_parent_object in parent_parent_objects:
                            po = parent_parent_object[parent[-1]]
                            if isinstance(po, list):
                                parent_objects.extend(po)
                            else:
                                parent_objects.append(po)
                        objects[tuple(parent)] = parent_objects

                    # add as a property we care about
                    objects_properties[tuple(parent)].append(child)

            # we now have all the objects and their properties in order, we'll do them in reverse to prevent dangling
            # references
            for key, obj_list in reversed(objects.items()):
                for obj in obj_list:
                    meta_world.know(agent_world, obj, objects_properties[key])
        elif isinstance(stmt, ForgetNode):
            pass
        elif isinstance(stmt, PassNode):
            pass
        else:
            raise CaseException

    def agent_done(self, agent_name: str) -> bool:
        return self.agent_done[agent_name]

    def all_agents_done(self) -> bool:
        for v in self.agent_done.values():
            if not v:
                return False
        return True

    def state(self):
        pass
