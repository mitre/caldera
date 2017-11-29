# Generated from C:/Users/dpmiller/projects/caldera/caldera/app/cddl\cddl.g4 by ANTLR 4.7
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .cddlParser import cddlParser
else:
    from cddlParser import cddlParser

# This class defines a complete listener for a parse tree produced by cddlParser.
class cddlListener(ParseTreeListener):

    # Enter a parse tree produced by cddlParser#actions.
    def enterActions(self, ctx:cddlParser.ActionsContext):
        pass

    # Exit a parse tree produced by cddlParser#actions.
    def exitActions(self, ctx:cddlParser.ActionsContext):
        pass


    # Enter a parse tree produced by cddlParser#action.
    def enterAction(self, ctx:cddlParser.ActionContext):
        pass

    # Exit a parse tree produced by cddlParser#action.
    def exitAction(self, ctx:cddlParser.ActionContext):
        pass


    # Enter a parse tree produced by cddlParser#name.
    def enterName(self, ctx:cddlParser.NameContext):
        pass

    # Exit a parse tree produced by cddlParser#name.
    def exitName(self, ctx:cddlParser.NameContext):
        pass


    # Enter a parse tree produced by cddlParser#description.
    def enterDescription(self, ctx:cddlParser.DescriptionContext):
        pass

    # Exit a parse tree produced by cddlParser#description.
    def exitDescription(self, ctx:cddlParser.DescriptionContext):
        pass


    # Enter a parse tree produced by cddlParser#knowns.
    def enterKnowns(self, ctx:cddlParser.KnownsContext):
        pass

    # Exit a parse tree produced by cddlParser#knowns.
    def exitKnowns(self, ctx:cddlParser.KnownsContext):
        pass


    # Enter a parse tree produced by cddlParser#known.
    def enterKnown(self, ctx:cddlParser.KnownContext):
        pass

    # Exit a parse tree produced by cddlParser#known.
    def exitKnown(self, ctx:cddlParser.KnownContext):
        pass


    # Enter a parse tree produced by cddlParser#known_assign.
    def enterKnown_assign(self, ctx:cddlParser.Known_assignContext):
        pass

    # Exit a parse tree produced by cddlParser#known_assign.
    def exitKnown_assign(self, ctx:cddlParser.Known_assignContext):
        pass


    # Enter a parse tree produced by cddlParser#wheres.
    def enterWheres(self, ctx:cddlParser.WheresContext):
        pass

    # Exit a parse tree produced by cddlParser#wheres.
    def exitWheres(self, ctx:cddlParser.WheresContext):
        pass


    # Enter a parse tree produced by cddlParser#where_expr.
    def enterWhere_expr(self, ctx:cddlParser.Where_exprContext):
        pass

    # Exit a parse tree produced by cddlParser#where_expr.
    def exitWhere_expr(self, ctx:cddlParser.Where_exprContext):
        pass


    # Enter a parse tree produced by cddlParser#effects.
    def enterEffects(self, ctx:cddlParser.EffectsContext):
        pass

    # Exit a parse tree produced by cddlParser#effects.
    def exitEffects(self, ctx:cddlParser.EffectsContext):
        pass


    # Enter a parse tree produced by cddlParser#stmts.
    def enterStmts(self, ctx:cddlParser.StmtsContext):
        pass

    # Exit a parse tree produced by cddlParser#stmts.
    def exitStmts(self, ctx:cddlParser.StmtsContext):
        pass


    # Enter a parse tree produced by cddlParser#If.
    def enterIf(self, ctx:cddlParser.IfContext):
        pass

    # Exit a parse tree produced by cddlParser#If.
    def exitIf(self, ctx:cddlParser.IfContext):
        pass


    # Enter a parse tree produced by cddlParser#Create.
    def enterCreate(self, ctx:cddlParser.CreateContext):
        pass

    # Exit a parse tree produced by cddlParser#Create.
    def exitCreate(self, ctx:cddlParser.CreateContext):
        pass


    # Enter a parse tree produced by cddlParser#Knows.
    def enterKnows(self, ctx:cddlParser.KnowsContext):
        pass

    # Exit a parse tree produced by cddlParser#Knows.
    def exitKnows(self, ctx:cddlParser.KnowsContext):
        pass


    # Enter a parse tree produced by cddlParser#Forget.
    def enterForget(self, ctx:cddlParser.ForgetContext):
        pass

    # Exit a parse tree produced by cddlParser#Forget.
    def exitForget(self, ctx:cddlParser.ForgetContext):
        pass


    # Enter a parse tree produced by cddlParser#For.
    def enterFor(self, ctx:cddlParser.ForContext):
        pass

    # Exit a parse tree produced by cddlParser#For.
    def exitFor(self, ctx:cddlParser.ForContext):
        pass


    # Enter a parse tree produced by cddlParser#Pass.
    def enterPass(self, ctx:cddlParser.PassContext):
        pass

    # Exit a parse tree produced by cddlParser#Pass.
    def exitPass(self, ctx:cddlParser.PassContext):
        pass


    # Enter a parse tree produced by cddlParser#knows_object.
    def enterKnows_object(self, ctx:cddlParser.Knows_objectContext):
        pass

    # Exit a parse tree produced by cddlParser#knows_object.
    def exitKnows_object(self, ctx:cddlParser.Knows_objectContext):
        pass


    # Enter a parse tree produced by cddlParser#obj_create.
    def enterObj_create(self, ctx:cddlParser.Obj_createContext):
        pass

    # Exit a parse tree produced by cddlParser#obj_create.
    def exitObj_create(self, ctx:cddlParser.Obj_createContext):
        pass


    # Enter a parse tree produced by cddlParser#eq_list.
    def enterEq_list(self, ctx:cddlParser.Eq_listContext):
        pass

    # Exit a parse tree produced by cddlParser#eq_list.
    def exitEq_list(self, ctx:cddlParser.Eq_listContext):
        pass


    # Enter a parse tree produced by cddlParser#obj.
    def enterObj(self, ctx:cddlParser.ObjContext):
        pass

    # Exit a parse tree produced by cddlParser#obj.
    def exitObj(self, ctx:cddlParser.ObjContext):
        pass


    # Enter a parse tree produced by cddlParser#ExprObj.
    def enterExprObj(self, ctx:cddlParser.ExprObjContext):
        pass

    # Exit a parse tree produced by cddlParser#ExprObj.
    def exitExprObj(self, ctx:cddlParser.ExprObjContext):
        pass


    # Enter a parse tree produced by cddlParser#ExprParen.
    def enterExprParen(self, ctx:cddlParser.ExprParenContext):
        pass

    # Exit a parse tree produced by cddlParser#ExprParen.
    def exitExprParen(self, ctx:cddlParser.ExprParenContext):
        pass


    # Enter a parse tree produced by cddlParser#ExprString.
    def enterExprString(self, ctx:cddlParser.ExprStringContext):
        pass

    # Exit a parse tree produced by cddlParser#ExprString.
    def exitExprString(self, ctx:cddlParser.ExprStringContext):
        pass


    # Enter a parse tree produced by cddlParser#ExprComp.
    def enterExprComp(self, ctx:cddlParser.ExprCompContext):
        pass

    # Exit a parse tree produced by cddlParser#ExprComp.
    def exitExprComp(self, ctx:cddlParser.ExprCompContext):
        pass


    # Enter a parse tree produced by cddlParser#ExprExist.
    def enterExprExist(self, ctx:cddlParser.ExprExistContext):
        pass

    # Exit a parse tree produced by cddlParser#ExprExist.
    def exitExprExist(self, ctx:cddlParser.ExprExistContext):
        pass


    # Enter a parse tree produced by cddlParser#ExprNot.
    def enterExprNot(self, ctx:cddlParser.ExprNotContext):
        pass

    # Exit a parse tree produced by cddlParser#ExprNot.
    def exitExprNot(self, ctx:cddlParser.ExprNotContext):
        pass


    # Enter a parse tree produced by cddlParser#ExprBool.
    def enterExprBool(self, ctx:cddlParser.ExprBoolContext):
        pass

    # Exit a parse tree produced by cddlParser#ExprBool.
    def exitExprBool(self, ctx:cddlParser.ExprBoolContext):
        pass


    # Enter a parse tree produced by cddlParser#ExprBinComp.
    def enterExprBinComp(self, ctx:cddlParser.ExprBinCompContext):
        pass

    # Exit a parse tree produced by cddlParser#ExprBinComp.
    def exitExprBinComp(self, ctx:cddlParser.ExprBinCompContext):
        pass


    # Enter a parse tree produced by cddlParser#bool_val.
    def enterBool_val(self, ctx:cddlParser.Bool_valContext):
        pass

    # Exit a parse tree produced by cddlParser#bool_val.
    def exitBool_val(self, ctx:cddlParser.Bool_valContext):
        pass


    # Enter a parse tree produced by cddlParser#NE.
    def enterNE(self, ctx:cddlParser.NEContext):
        pass

    # Exit a parse tree produced by cddlParser#NE.
    def exitNE(self, ctx:cddlParser.NEContext):
        pass


    # Enter a parse tree produced by cddlParser#IN.
    def enterIN(self, ctx:cddlParser.INContext):
        pass

    # Exit a parse tree produced by cddlParser#IN.
    def exitIN(self, ctx:cddlParser.INContext):
        pass


    # Enter a parse tree produced by cddlParser#EQ.
    def enterEQ(self, ctx:cddlParser.EQContext):
        pass

    # Exit a parse tree produced by cddlParser#EQ.
    def exitEQ(self, ctx:cddlParser.EQContext):
        pass


    # Enter a parse tree produced by cddlParser#bin_comp.
    def enterBin_comp(self, ctx:cddlParser.Bin_compContext):
        pass

    # Exit a parse tree produced by cddlParser#bin_comp.
    def exitBin_comp(self, ctx:cddlParser.Bin_compContext):
        pass


