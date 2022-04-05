module.exports = {
    ci: {
        assert: {
            preset: 'lighthouse:recommended',
        },
        collect: {
            staticDistDir: './templates'
            url: ['http://localhost:8888/'],
            startServerCommand: ' python3 server.py --insecure --fresh -l DEBUG',
        },
        upload: {
            target: 'temporary-public-storage',
        },
    },
};
