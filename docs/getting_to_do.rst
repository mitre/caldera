===================================
Getting CALDERA to do What You Want
===================================

**CALDERA** is designed to be completely automated. In creating a completely automated system, there
is a natural tension between letting the system decide what to do, and telling the system what to do. The
design of **CALDERA** emphasizes the former: **CALDERA** decides for itself what to do.

**CALDERA** makes this decision based on an internal heuristic that grades possibles courses of action.
**CALDERA** can be customized by modifying this internal heuristic. At the moment this can only be done by
editing the source code. **CALDERA**'s heuristic is straightforward, each step has a numeric score called a ``value``\ .
Higher ``value``\ s indicate a higher precedence step. Steps with higher precedence are prioritized over steps with
lower precedence.

**CALDERA**'s built-in step values can be modified by editing the file ``/caldera/caldera/app/operation/operation_steps.py``