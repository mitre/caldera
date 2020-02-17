Docker deployment
===============

If you wish to run CALDERA from a Docker container, execute the commands below.

1. Build a container from the latest changes.
```
docker build . -t caldera:server
```

2. Run the docker CALDERA server
```
docker run -p 7010:7010 -p 7011:7011 -p 7012:7012 -p 8888:8888 caldera:server
```