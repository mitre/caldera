module.exports = {
    ci: {
        assert: {
            "assertMatrix": [
                {
                  "matchingUrlPattern": ".*",
                  "assertions": {
                    "html-has-lang": "off",
                    "html-lang-valid": "off",
                    "document-title": "off",
                    "list": "off",
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
