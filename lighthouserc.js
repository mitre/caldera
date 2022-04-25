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
                    "categories:accessibility": ["error", {"minScore": 0.75}]
                  }
                }
            ],
        },
        collect: {
            numberOfRuns: 1,
            maxAutodiscoverUrls: 0,
            staticDistDir: '\\/templates\\/?[a-zA-Z0-9.-]+\.(html)$'
        },
        upload: {
            target: 'temporary-public-storage'
        },
    },
};
