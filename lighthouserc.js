module.exports = {
    ci: {
        assert: {
            "assertMatrix": [
                {
                  "matchingUrlPattern": ".*",
                  "assertions": {
                    "categories:accessibility": ["error", {"minScore": 0.8}]
                  }
                }
            ],
        },
        collect: {
            numberOfRuns: 1,
            maxAutodiscoverUrls: 0,
            staticDistDir: './templates'
        },
        upload: {
            target: 'temporary-public-storage'
        },
    },
};
