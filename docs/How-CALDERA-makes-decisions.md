How CALDERA makes decisions
=========================

CALDERA makes decisions using parsers, which are optional blocks inside an ability.

Let's look at an example snippet of an ability that uses a parser:
```
    darwin:
      sh:
        command: |
          find /Users -name '*.#{file.sensitive.extension}' -type f -not -path '*/\.*' 2>/dev/null
        parsers:
          plugins.stockpile.app.parsers.basic:
            - source: host.file.sensitive
              edge: has_extension
              target: file.sensitive.extension
```

A parser is identified by the module which contains the code to parse the command's output. The parser can contain: 

**Source** (required): A fact to create for any matches from the parser

**Edge** (optional): A relationship between the source and target. This should be a string.

**Target** (optional): A fact to create which the source connects too.

In the above example, the output of the command will be sent through the plugins.stockpile.app.parsers.basic module, which will create a relationship for every found file.