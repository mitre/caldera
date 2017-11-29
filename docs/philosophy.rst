====================
CALDERA's Philosophy
====================

**CALDERA** is an automated adversary emulation system produced by the MITRE Corporation.
It is designed to operate on Windows Enterprise networks.

Adversary Emulation
===================

Adversary Emulation is a branch of **red teaming**. The purpose of red teaming is to approach a
problem or system as an adversary would, with the mindset of breaking the system, abusing it, or
otherwise maliciously interfering with it. The practice of red teaming is commonly used as a method to
test and improve the security of a system by iteratively breaking a system as an attacker would
and mitigating those attacks. Red teaming is often focused on demonstrating the risk of an
adversary's impact to an organization. Engagements may take weeks or months and one of the goals of the
red team is to not be detected.

Adversary Emulation is at its core red teaming, but rather than using the general mindset of a attacker,
adversary emulation adopts the methodologies of a specific real-world adversary, complete with
the adversary's goals, methods, and techniques based on threat intelligence on how that adversary is known
to operate. The focus of engagements is on having the emulation team and the defenders work together to improve
the systems, network, and defensive processes to better detect the techniques used across the adversary's lifecycle.
Adversary Emulation grounds the process of red teaming by focusing on threats that are demonstratively real in a way
that defensive improvements can be measured and verified.

Why Adversary Emulation?
========================

The practice of emulating adversaries is designed to answer the question: "Is my network secure?". Or
more specifically: "Is my network secure against known threats?".

As with all things, the best way to find out something is to test it. The same applies to networks:
the best way to find out if a network is resilient to adversary attack
is to actually enact adversary actions on that network and observe how the network responds.

Automating Adversary Emulation
==============================

**CALDERA** automates adversary emulation. CALDERA contains numerous built
in adversary techniques that are derived from `ATT&CK <https://attack.mitre.org>`_. For each adversary technique,
CALDERA contains a logical encoding that describes that technique's requirements (preconditions) and the effects of
the techniques (postconditions). CALDERA uses this information to figure out when and how to execute the
actions that it is told to use.

Post Compromise
===============

**CALDERA** is focused on adversary emulation "post compromise". In other words, CALDERA assumes that
an adversary already has an initial foothold on a network. **CALDERA** emulates adversary
actions that occur after this point of initial compromise. This concept of "post compromise"
has several important implications:

**CALDERA** doesn't focus on the things an adversary will do to "get in". Things like vulnerability
scanning, penetration testing, intelligence gathering, and spearphising, that commonly occur as
a precursor to an attack are out of scope for **CALDERA**.

**CALDERA**'s behavior reflects what attackers do after initially compromising a network, which
is significantly
different from how they behave before compromising a network. For many, the mental model
of how computer networks are compromised usually involves executing a string of
exploits against systems to penetrate into a network. However, in reality exploits are rarely
used post compromise. Instead attackers leverage built-in functionality and tools of the
network. This means that unlike other automation systems **CALDERA** places a heavy emphasis on
using and abusing these same constructs.

In assuming that an attacker has already compromised a network, **CALDERA** exercises areas of
defenses that are commonly weak and untested within networks. Significant emphasis is usually placed on
perimeter defenses (things like firewalls, boundary packet inspection, and maintaining DMZ patch levels)
at the expense of post compromise defenses. In other words, defenses meant to prevent initial
compromise are heavily stressed, often at the expense of defenses designed to prevent or
detect post-compromise activity. **CALDERA**'s post compromise focus means that it
tests areas of security that are typically neglected.