What is a rule?
============

A Rule is a way of restricting or placing boundaries on CALDERA. Rules are directly related to [facts](What-is-a-fact.md) and should be included in a fact sheet.

Rules act similar to firewall rules and have three key components: fact, action, and match
1. **Fact** specifies the name of the fact that the rule will apply to.
2. **Action** (ALLOW,DENY) will allow or deny the fact from use if it matches the rule.
3. **Match** regex rule on a fact's value to determine if the rule applies.

During an operation, the planning service matches each link against the rule-set, discarding it if any of the fact assignments in the link match a rule specifying DENY and keeping it otherwise. In the case that multiple rules match the same fact assignment, the last one listed will be given priority.

**Example**
```
rules:
  - action: DENY
    fact: file.sensitive.extension
    match: .*
  - action: ALLOW
    fact: file.sensitive.extension
    match: txt
```
In this example only the txt file extension will be used. Note that the ALLOW action for txt supersedes the DENY for all, as the ALLOW rule is listed later in the policy. If the ALLOW rule was listed first, and the DENY rule second, then all values (including txt) for file.sensitive.extension would be discarded.

### Subnets
Rules can also match against subnets.

**Subnet Example**
```
  - action: DENY
    fact: my.host.ip
    match: .*
  - action: ALLOW
    fact: my.host.ip
    match: 10.245.112.0/24
```
In this example, the rules would permit CALDERA to only operate within the 10.245.112.1 to 10.245.112.254 range
