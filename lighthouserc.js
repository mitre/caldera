module.exports = {
    ci: {
      assert: {
        assertions: {
            "categories:accessibility": ["error", {"minScore": 0.9}]
        }
      },
      collect: {
        url: ['http://localhost:8888/'],
        startServerCommand: ' python3 server.py --insecure --fresh -l DEBUG',
      },
      upload: {
        target: 'temporary-public-storage',
      },
    },
};
