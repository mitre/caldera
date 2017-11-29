from itertools import zip_longest
import collections
from typing import List

from antlr4 import *

from .gen.cddlParser import cddlParser
from .gen.cddlListener import cddlListener
from . import ast
from .util import CaseException, Trie
from .schema import VarStore
from .gen.cddlLexer import cddlLexer
from . import optimize


class Action(object):
    def __init__(self, schema):
        self.name = ""
        self.description = ""
        self.knowns = []
        self.preconditions = []
        self.effects = []
        self.vb = VarStore(schema)
        self.predicate_store = []

    def __repr__(self):
        return "Action '{}'\n\t{}\nKnowns:\n{}\nEffects:\n{}"\
            .format(self.name, self.description, "\n".join(self.knowns), self.effects)


class LogicGenerator(cddlListener):
    def __init__(self, schema):
        self.actions = []
        self.cur_action = None
        self.schema = schema
        self.namespace_stack = collections.deque()
        self.types_stack = collections.deque()

    def enterAction(self, ctx: cddlParser.ActionContext):
        self.cur_action = Action(self.schema)
        self.actions.append(self.cur_action)
        if ctx.name():
            self.cur_action.name = ctx.name().ID().getText()
        else:
            self.cur_action.name = None
        if ctx.description():
            self.cur_action.description = ctx.description().STRING().getText()[1:-1]
        else:
            self.cur_action.description = None

    def enterKnown(self, ctx):
        head = Trie()
        for ka in ctx.known_assign().known_assign():
            self.build_known_trie(ka, head)

        self.cur_action.preconditions.append(ast.DefineNode(name=ctx.ID().getText(),
                                                            typ=ctx.known_assign().ID().getText(),
                                                            obj=head))

    def enterWhere_expr(self, ctx: cddlParser.Where_exprContext):
        assert ctx.comp().getText() in ("!=", "==")
        self.cur_action.preconditions.append(ast.CompNode(ctx.obj(0).getText(), ctx.comp().getText(),
                                                          ctx.obj(1).getText()))

    def enterEffects(self, ctx: cddlParser.EffectsContext):
        self.cur_action.effects = self.buildStmts(ctx.stmts(0))

    def buildStmts(self, stmts: cddlParser.StmtsContext):
        retval = []
        for x in stmts.stmt():
            retval.extend(self.buildStmt(x))
        return retval

    def buildStmt(self, stmt: cddlParser.StmtContext) -> List[ast.StatementNode]:
        if isinstance(stmt, cddlParser.IfContext):
            ast_node = ast.IfElNode()
            for i, (expr, stmts) in enumerate(zip_longest(stmt.expr(), stmt.stmts())):
                if i == 0:
                    ast_node.expr = self.buildExpr(expr)
                    ast_node.stmts = self.buildStmts(stmts)
                elif not expr:
                    ast_node.else_stmts = self.buildStmts(stmts)
                else:
                    ast_node.elif_expr_stmts.append((self.buildExpr(expr), self.buildStmts(stmts)))
            return [ast_node]
        elif isinstance(stmt, cddlParser.CreateContext):
            ident, pairs = self.buildObj_create(stmt.obj_create())
            return [ast.CreateNode(ident=ident, field_values=pairs)]
        elif isinstance(stmt, cddlParser.KnowsContext):
            return [ast.KnowNode(obj=self.build_knows_trie(stmt.knows_object()))]
        elif isinstance(stmt, cddlParser.ForgetContext):
            return [ast.ForgetNode(obj=self.build_knows_trie(stmt.knows_object()))]
        elif isinstance(stmt, cddlParser.ForContext):
            return [ast.ForNode(ident=stmt.ID().getText(), obj=stmt.obj().getText(), stmts=self.buildStmts(stmt.stmts()))]
        elif isinstance(stmt, cddlParser.PassContext):
            return [ast.PassNode()]
        else:
            raise CaseException

    def buildExpr(self, expr: cddlParser.ExprContext):
        if isinstance(expr, cddlParser.ExprParenContext):
            return ast.ParenNode(expr=self.buildExpr(expr.expr()))
        elif isinstance(expr, cddlParser.ExprNotContext):
            return ast.NotNode(expr=self.buildExpr(expr.expr()))
        elif isinstance(expr, cddlParser.ExprExistContext):
            return ast.ExistNode(expr=self.buildExpr(expr.expr()))
        elif isinstance(expr, cddlParser.ExprCompContext):
            return ast.CompNode(left=self.buildExpr(expr.expr(0)), comp=expr.comp().getText(),
                                right=self.buildExpr(expr.expr(1)))
        elif isinstance(expr, cddlParser.ExprBinCompContext):
            return ast.BinCompNode(left=self.buildExpr(expr.expr(0)), comp=expr.bin_comp().getText(),
                                   right=self.buildExpr(expr.expr(1)))
        elif isinstance(expr, cddlParser.ExprObjContext):
            return ast.ObjNode(obj=expr.obj().getText())
        elif isinstance(expr, cddlParser.ExprStringContext):
            return expr.STRING().getText()
        elif isinstance(expr, cddlParser.ExprBoolContext):
            if expr.bool_val().getText() == "True":
                return True
            elif expr.bool_val().getText() == "False":
                return False
            else:
                raise CaseException
        else:
            raise CaseException

    def build_known_trie(self, ctx: cddlParser.Known_assignContext, head=None) -> Trie:
        if head is None:
            head = Trie()

        head.add_item([ctx.ID().getText()])
        for x in ctx.known_assign():
            self.build_known_trie(x, head.children[ctx.ID().getText()])
        return head

    def build_knows_trie(self, ctx: cddlParser.Knows_objectContext, head=None) -> Trie:
        if head is None:
            head = Trie()

        head.add_item([ctx.obj().getText()])
        for x in ctx.knows_object():
            self.build_knows_trie(x, head.children[ctx.obj().getText()])
        return head

    def buildEq_list(self, ctx: cddlParser.Eq_listContext):
        return ctx.ID().getText(), self.buildExpr(ctx.expr()) if ctx.expr() else None

    def buildObj_create(self, ctx: cddlParser.Obj_createContext):
        return ctx.ID().getText(), [self.buildEq_list(x) for x in ctx.eq_list()]


def get_ast(cddl: str, schema_json: dict):
    lexer = cddlLexer(InputStream(cddl))
    stream = CommonTokenStream(lexer)
    parser = cddlParser(stream)
    tree = parser.actions()
    logic = LogicGenerator(schema_json)
    walker = ParseTreeWalker()
    walker.walk(logic, tree)

    for action in logic.actions:
        action.effects = optimize.ast_optimize(action.effects)

    return logic.actions
