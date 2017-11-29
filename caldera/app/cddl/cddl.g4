// Define a grammar called cddl
grammar cddl;

// Parser rules
actions : action+ EOF;

action : (name)? (description)? knowns (wheres)? effects ;

name : 'Name:' ID ;

description : 'Description:' STRING ;

knowns : 'Knowns:' (known)* ;

known : ID ':' known_assign ; 

known_assign :
  ID
| ID '[' known_assign (',' known_assign)* ']';

wheres : 'Where:' (where_expr)* ;

where_expr: obj comp obj ;

effects : 'Effects:' (stmts)* ;

stmts: (stmt)+ ;

stmt : 
  'if' expr '{' stmts '}' ('elif' expr '{' stmts '}' )* ('else' '{' stmts '}' )? # If
| 'create' obj_create # Create
| 'know' knows_object # Knows
| 'forget' knows_object # Forget
| 'for' ID 'in' obj '{' stmts '}' # For 
| 'pass' # Pass;

knows_object : 
  obj
| obj '[' knows_object (',' knows_object)* ']' ; 

obj_create :
  ID '[' eq_list (',' eq_list)*']' ;

eq_list : 
  ID 
| ID '=' expr ;

obj : ID ('.' ID)* ;

expr: 
  '(' expr ')' # ExprParen
| 'not' expr # ExprNot
| 'exist' expr # ExprExist
| left=expr comp right=expr # ExprComp
| left=expr bin_comp right=expr # ExprBinComp
| bool_val # ExprBool
| obj # ExprObj
| STRING # ExprString ; 

bool_val : 
 'True'
| 'False';

comp : 
  '!=' # NE
| 'in' # IN
| '==' # EQ ;

bin_comp :
  'and' 
| 'or' ;

// Lexer rules
STRING : '"' ('""'|~'"')* '"' ;
ID : [a-zA-Z_][a-zA-Z_0-9]* ;  // match identifiers
COMMENT : '#' ~[\r\n]* -> skip ; // skip comment lines
WS : [ \t\r\n]+ -> skip ; // skip spaces, tabs, newlines