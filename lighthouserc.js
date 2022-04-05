module.exports = {
    ci: {
        assertions: {
            "categories:accessibility": ["error", {"minScore": 0.9}]
        },
        collect: {
            numberOfRuns: 1,
            staticDistDir: './templates',
        },
        upload: {
            target: 'temporary-public-storage',
        },
    },
};
