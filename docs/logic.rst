================
Logic in CALDERA
================

.. note:: This section is subject to heavy development and likely to change in future versions of **CALDERA**

Logic is a central part of how **CALDERA** is able to operate automatically.

Every Adversary action, called a *Step* in **CALDERA**, contains a logical description of the Step's requirements
and effects. **CALDERA** parses these logical descriptions to both tell when it is possible to run a Step and
to predict the outcome of a Step. This lets **CALDERA** generate plans by iteratively checking what Steps are
executable given the current state, selecting a Step, and then generating the output state of that step, all
according to the logical rules.

**CALDERA**'s behavior is based on the branch of Artificial Intelligence called Planning.
`An introduction to Planning is available on Wikipedia <https://en.wikipedia.org/wiki/Automated_planning_and_scheduling>`_
