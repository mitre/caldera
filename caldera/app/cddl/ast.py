from typing import List
from .util import Trie


class StatementNode(object):
    pass


class ExprNode(object):
    pass


class DefineNode(StatementNode):
    def __init__(self, name: str, typ: str, obj: Trie=None) -> None:
        self.name = name
        self.typ = typ
        self.obj = obj

    def __repr__(self):
        return "define {} = {}[{}]".format(self.name, self.typ, self.obj)


class IfNode(StatementNode):
    def __init__(self, expr: ExprNode, stmts: List[StatementNode]) -> None:
        self.expr = expr
        self.stmts = stmts

    def __repr__(self):
        ifstr = "if {} {{\n{}\n}}".format(self.expr, self.stmts)
        return ifstr


class IfElNode(StatementNode):
    def __init__(self, expr: ExprNode=None, stmts: List[StatementNode]=None, elif_expr_stmts=None,
                 else_stmts: List[StatementNode]=None) -> None:
        self.expr = expr
        self.stmts = stmts if stmts is not None else []
        self.elif_expr_stmts = elif_expr_stmts if elif_expr_stmts is not None else []
        self.else_stmts = else_stmts if else_stmts is not None else []

    def __repr__(self):
        ifstr = "if {} {{\n{}\n}}".format(self.expr, self.stmts)

        if self.elif_expr_stmts:
            for expr, stmts in self.elif_expr_stmts:
                ifstr += " elif {} {{\n{}\n}}".format(expr, stmts)
        if self.else_stmts:
            ifstr += " else {{\n{}\n}}".format(self.else_stmts)
        return ifstr


class ForNode(StatementNode):
    def __init__(self, ident: str=None, obj: str =None, stmts: List[StatementNode]=None) -> None:
        self.ident = ident
        self.obj = obj
        self.stmts = stmts if stmts is not None else []

    def __repr__(self):
        return "for {} in {} {{\n{}\n}}".format(self.ident, self.obj, self.stmts)


class CreateNode(StatementNode):
    def __init__(self, ident: str=None, field_values=None) -> None:
        self.ident = ident
        self.field_values = field_values if field_values is not None else []

    def __repr__(self):
        pairs = []
        for x, y in self.field_values:
            if y:
                pairs.append("{}={}".format(x, y))
            else:
                pairs.append(str(x))
        return "create {}[{}]".format(self.ident, ",".join(pairs))


class KnowNode(StatementNode):
    def __init__(self, obj: Trie=None) -> None:
        self.obj = obj

    def __repr__(self):
        return "know {}".format(self.obj)


class ForgetNode(StatementNode):
    def __init__(self, obj: Trie=None) -> None:
        self.obj = obj

    def __repr__(self):
        return "forget {}".format(self.obj)


class PassNode(StatementNode):
    pass


class ParenNode(ExprNode):
    def __init__(self, expr: ExprNode=None) -> None:
        self.expr = expr

    def __repr__(self):
        return "({})".format(self.expr)


class NotNode(ExprNode):
    def __init__(self, expr: ExprNode=None) -> None:
        self.expr = expr

    def __repr__(self):
        return "not {}".format(self.expr)


class ExistNode(ExprNode):
    def __init__(self, expr: ExprNode=None) -> None:
        self.expr = expr

    def __repr__(self):
        return "exist {}".format(self.expr)


# !=, ==, in
class CompNode(ExprNode):
    def __init__(self, left: ExprNode=None, comp: str=None, right: ExprNode=None) -> None:
        self.left = left
        self.comp = comp
        self.right = right

    def __repr__(self):
        return "{} {} {}".format(self.left, self.comp, self.right)


# and, or
class BinCompNode(ExprNode):
    def __init__(self, left: ExprNode=None, comp: str=None, right: ExprNode=None) -> None:
        self.left = left
        self.comp = comp
        self.right = right

    def __repr__(self):
        return "{} {} {} ".format(self.left, self.comp, self.right)


class ObjNode(ExprNode):
    def __init__(self, obj: str=None) -> None:
        self.obj = obj

    def __repr__(self):
        return self.obj
