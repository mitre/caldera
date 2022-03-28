module.exports = {
    ci: {
      collect: {
        url: ['http://localhost:8888/'],
        startServerCommand: ' python3 server.py --insecure --fresh -l DEBUG',
      },
      upload: {
        target: 'temporary-public-storage',
      },
    },
};
