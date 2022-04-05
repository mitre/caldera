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
                    "categories:accessibility": ["error", {"minScore": 0.9}]
                  }
                }
            ],
        },
        collect: {
            numberOfRuns: 2,
            maxAutodiscoverUrls: 1,
            staticDistDir: './templates'
        },
        upload: {
            target: 'temporary-public-storage'
        },
    },
};
