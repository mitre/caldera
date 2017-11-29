===========
Limitations
===========

**CALDERA** is a working prototype, several decisions have been made to limit its scope.
This section details several of these decisions.

No Command and Control Emulation
    We decided not to emulate Command and Control (C2) channels.
    This may seem like a glaring omission, but it was made for several reasons.
    For one, several tools already exist for simulating C2 network traffic. We felt that
    we could make a greater impact by focusing on other aspects of emulation, such as generating host-based artifacts.

    From a practical standpoint, **CALDERA** was originally created to test host-based defenses and sensors.
    For this use, C2 emulation activity
    was unnecessary since host-based defenses mainly use activity on the host and not on the network.

    From a philosophical standpoint, an adversary's Command and Control protocol
    is easy to change and has a multitude of variations. Due to the wide variation in possibilities
    we thought our time would be better spent emulating other aspects of adversary behavior.

No Linux Support
    **CALDERA** only supports Windows Environments, Windows is nearly ubiquitous in corporate and
    government environments. Furthermore, most publicly adversary reports detailed techniques
    used on Windows, which are very specific to given operating systems.
    Despite this, more information is becoming available on adversary behavior on Linux systems.
    We would like to eventually add Linux support to **CALDERA**.