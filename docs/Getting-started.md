Getting started
====================

Before you start using CALDERA, you should determine how you'd like to use it. Because it is a cyber security 
framework, there are several ways you can utilize it - from offensive (red) to defensive (blue).

Here are the most common use-cases and basic instructions on how to proceed. 

## Autonomous red-team engagements

This is the original CALDERA use-case. You can use the framework to build a specific threat (adversary) 
profile and launch it in a network to see where you may be susceptible. This is good for testing defenses
and training blue teams on how to detect threats. 

To use this:

1) Log in as a red user
2) Click into the Sandcat plugin and deploy an agent on any compromised host
3) Review or build threat profiles in the Profiles tab. Hint: getting experienced red-team operators to build these
profiles allows the blue team to re-run them anytime they want in the future.
4) Launch an operation against your agents using any threat profile 

All built-in threat profiles are safe to use out-of-the-box. 

## Manual red-team engagements

You can use CALDERA to perform manual red-team assessments by leveraging the terminal plugin. This is good for 
replacing or appending existing offensive toolsets in a manual assessment, as the framework can be extended 
with any custom tools you may have.

To use this:

1) Log in as a red user
2) Click into the terminal plugin and deploy the Manx agent on any compromised host
4) Use the created sessions inside the terminal emulator to perform manual commands

## Autonomous incident-response 

You can leverage CALDERA to perform automated incident response on a given host. This is helpful for identifying 
TTPs that other security tools may not see or block. 

To use this:

1) Log in as a blue user
2) Click into the Sandcat plugin and deploy an agent on any host
3) Review or build defender profiles in the Profiles tab
4) Launch an operation against your agents using any defender profile 

Defender profiles utilize fact sources to determine good vs. bad on a given host.

## Research on artificial intelligence

You can ignore all red/blue and security aspects of CALDERA and instead use it to test artificial intelligence and
other decision-making algorithms. 

To use this:

1) Enable the mock plugin and restart the server. Log in as a red user.
2) In the Campaigns -> Agents tab, review the simulated agents that have been spun up
3) Run an operation using any adversary against your simulated agents. Note how the operation runs non-deterministically. You can now go into the sequential.py planning module and adjust the logic which 
makes decisions on what to do when to test out different theories. 