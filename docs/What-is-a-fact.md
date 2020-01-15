What is a fact?
============

A fact is an identifiable piece of information about a given computer. Facts are directly related to variables, which can be used inside abilities. 

Facts are composed of a:
* **property**: a 3-part descriptor which identifies the type of fact. An example is host.user.name. A fact with this property tells me that it is a user name. This format allows you to specify the major (host) minor (user) and specific (name) components of each fact.
* **value**: any arbitrary string. An appropriate value for a host.user.name may be "Administrator" or "John". 
* **score**: an integer which associates a relative importance for the fact. Every fact, by default, gets a score of 1. If a host.user.password fact is important or has a high chance of success if used, you may assign it a score of 5. When an ability uses a fact to fill in a variable, it will use those with the highest scores first. If a fact has a score of 0, it will be blacklisted - meaning it cannot be used in the operation.

> If a property has a major component = host (e.g., host.user.name) that fact will only be used by the host that collected it.

As hinted above, when CALDERA runs abilities, it scans the command and cleanup instructions for variables. When it finds one, it then looks at the facts it has and sees if it can replace the variables with matching facts (based on the property). It will then create new variants of each command/cleanup instruction for each possible combination of facts it has collected. Each variant will be scored based on the cumulative score of all facts inside the command. The highest scored variants will be executed first. 

A fact source is a collection of facts that you have grouped together. A fact source can be applied to an operation when you start it, which gives the operation facts to fill in variables with. 

To set boundaries on facts and which values can be used see: [rules](What-is-a-rule.md)
