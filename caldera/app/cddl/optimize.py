from typing import List, Union, Tuple
import collections

from .util import CaseException
from .ast import StatementNode, ExistNode, NotNode, IfNode, IfElNode, BinCompNode, ExprNode, CompNode, ParenNode, \
    ForgetNode, ObjNode, CreateNode, ForNode, KnowNode, PassNode


# perform optimizations on the ast
def ast_optimize(stmts: List[StatementNode]) -> List[StatementNode]:
    es = TreeSubstitution()
    es.add_substition(ExistNode, _remove_exists)
    es.add_substition(NotNode, _remove_not)
    es.add_substition(IfNode, _branch_elimination)
    es.add_substition(IfElNode, _branch_unroll)
    es.add_substition(BinCompNode, _remove_and)
    return es.apply(stmts)


# remove exists
def _remove_exists(en: ExistNode) -> Union[bool, ExprNode]:
    return True


# "not" of True or False are evaluated
def _remove_not(notnode: NotNode) -> Union[bool, ExprNode]:
    if notnode.expr is True or notnode.expr is False:
        return not notnode.expr

    return notnode


# "and" of True or False values are evaluated
def _remove_and(bincomp: BinCompNode) -> Union[bool, ExprNode]:
    if bincomp.left is False or bincomp.right is False:
        return False
    if bincomp.left is True and bincomp.right is True:
        return True
    if bincomp.left is True:
        return bincomp.right
    if bincomp.right is True:
        return bincomp.left

    return bincomp


# Eliminate False branches, always execute True branches
def _branch_elimination(ifnode: IfNode) -> Tuple[bool, List[StatementNode]]:
    if ifnode.expr is True:
        return True, ifnode.stmts
    if ifnode.expr is False:
        return True, []
    return False, [ifnode]


# replace elif and else statements with if statements
def _branch_unroll(ifel: IfElNode) -> Tuple[bool, List[StatementNode]]:
    accum_guard = NotNode(expr=ifel.expr) # type: ExprNode
    ifs = [IfNode(expr=ifel.expr, stmts=ifel.stmts)]

    for expr, stmts in ifel.elif_expr_stmts:
        ifs.append(IfNode(expr=BinCompNode(left=accum_guard, comp="and", right=expr), stmts=stmts))
        accum_guard = BinCompNode(left=accum_guard, comp="and", right=NotNode(expr=expr))

    if ifel.else_stmts:
        ifs.append(IfNode(expr=accum_guard, stmts=ifel.else_stmts))
    return len(ifs) > 1, ifs


class TreeSubstitution(object):
    def __init__(self):
        self.applications = collections.defaultdict(list)

    def add_substition(self, expression_type, funcptr):
        self.applications[expression_type].append(funcptr)

    def apply_expr(self, expr) -> ExprNode:
        modification = expr
        for modifier in self.applications[type(modification)]:
            modification = modifier(modification)
            if modification != expr:
                return self.apply_expr(modification)

        pending = expr
        if isinstance(expr, ParenNode):
            mod = self.apply_expr(expr.expr)
            if mod != expr.expr:
                pending = ParenNode(expr=mod)
        elif isinstance(expr, NotNode):
            mod = self.apply_expr(expr.expr)
            if mod != expr.expr:
                pending = NotNode(expr=mod)
        elif isinstance(expr, ExistNode):
            mod = self.apply_expr(expr.expr)
            if mod != expr.expr:
                pending = ExistNode(expr=mod)
        elif isinstance(expr, CompNode):
            mod_left = self.apply_expr(expr.left)
            mod_right = self.apply_expr(expr.right)
            if mod_left != expr.left or mod_right != expr.right:
                pending = CompNode(left=mod_left, comp=expr.comp, right=mod_right)
        elif isinstance(expr, BinCompNode):
            mod_left = self.apply_expr(expr.left)
            mod_right = self.apply_expr(expr.right)
            if mod_left != expr.left or mod_right != expr.right:
                pending = BinCompNode(left=mod_left, comp=expr.comp, right=mod_right)
        elif isinstance(expr, ObjNode):
            pass
        elif isinstance(expr, bool):
            pass
        elif isinstance(expr, str):
            pass
        else:
            raise CaseException

        if pending != expr:
            return self.apply_expr(pending)
        return expr

    def apply_stmt(self, stmt: StatementNode) -> Tuple[bool, List[StatementNode]]:
        for modifier in self.applications[type(stmt)]:
            modified, modification = modifier(stmt)
            if modified:
                return self.apply_stmts(modification)

        pending = stmt
        if isinstance(stmt, IfNode):
            new_expr = self.apply_expr(stmt.expr)
            mod_stmts, new_stmts = self.apply_stmts(stmt.stmts)
            if new_expr != stmt.expr or mod_stmts:
                pending = IfNode(expr=new_expr, stmts=new_stmts)
        elif isinstance(stmt, CreateNode):
            new_field_values = [(x, self.apply_expr(y)) if y else (x, y) for x, y in stmt.field_values]
            if new_field_values != stmt.field_values:
                pending = CreateNode(ident=stmt.ident, field_values=new_field_values)
        elif isinstance(stmt, ForNode):
            modified, new_stmts = self.apply_stmts(stmt.stmts)
            if modified:
                pending = ForNode(ident=stmt.ident, obj=stmt.obj, stmts=new_stmts)
        elif isinstance(stmt, KnowNode):
            pass
        elif isinstance(stmt, ForgetNode):
            pass
        elif isinstance(stmt, PassNode):
            pass
        else:
            # IfElNode should be removed by the time we get to here
            raise CaseException

        if pending != stmt:
            return self.apply_stmt(pending)
        return False, [stmt]

    def apply_stmts(self, stmts: List[StatementNode]) -> Tuple[bool, List[StatementNode]]:
        bool_stmts = [self.apply_stmt(x) for x in stmts]
        b_val = False
        l_val = []
        for b, l in bool_stmts:
            b_val |= b
            l_val.extend(l)
        return b_val, l_val

    def apply(self, stmts: List[StatementNode]) -> List[StatementNode]:
        _, ret = self.apply_stmts(stmts)
        return ret
