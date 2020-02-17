Docker deployment
===============

If you wish to run CALDERA from a Docker container, execute the commands below.

1. Build a container from the latest changes.
```
docker build . -t caldera:server
```

2. Run the docker CALDERA server
```
docker run -p 8888:8888 caldera:server
```

Please note that if you have additional ports you're exposing to the container, you will have to pass additional arguments.

For example, if you were to allow the terminal plugin, port 5678 would have to be exposed thus requiring the following argument:

```
docker run -p 7010:7010 -p 7011:7011 -p 7012:7012 -p 8888:8888 caldera:server
```
