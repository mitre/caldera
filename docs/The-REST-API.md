The REST API
============

All REST API functionality can be viewed in the rest_api.py module in the source code.

### /api/rest

You can interact with all parts of CALDERA through the core REST API endpoint /api/rest. 

> Any request to this endpoint must include an "index" as part of the request, which routes it to the appropriate object type. 

Here are the available REST API functions:

#### DELETE

##### Agents

Delete any agent. 

```bash
curl -X DELETE http://localhost:8888/api/rest -d '{"index":"agents","paw":"$agent_paw"}'
```

##### Operations

Delete any operation.

```bash
curl -X DELETE http://localhost:8888/api/rest -d '{"index":"operations","id":"$operation_id"}'
```

#### PUT
                    
#### POST
        
### /file/upload

Files can be uploaded to CALDERA by POST'ing a file to the /file/upload endpoint. Uploaded files will be put in the exfil_dir location specified in the default.yml file.

#### Example
```bash
curl -F 'data=@path/to/file' http://localhost:8888/file/upload
```

### /file/download

Files can be dowloaded from CALDERA through the /file/download endpoint. This endpoint requires an HTTP header called "file" with the file name as the value. When a file is requested, CALDERA will look inside each of the payload directories listed in the local.yml file until it finds a file matching the name.

Files can also be downloaded indirectly through the [payload block of an ability](What-is-an-ability.md).

> Additionally, the [54ndc47 plugin](Plugins-sandcat.md) delivery commands utilize the file download endpoint to drop the agent on a host

#### Example
```bash
curl -X POST -H "file:wifi.sh" http://localhost:8888/file/download > wifi.sh
```