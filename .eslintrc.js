module.exports = {
    plugins: [
        "html"
    ],
    extends: "airbnb-base",
    env: {
        browser: true,
        es2021: true,
        jquery: true
    },
    parserOptions: {
        ecmaVersion: 12
    },
    globals: {
        stream: "readonly",
        restRequest: "readonly",
        certificates: "readonly"
    },
    rules: {
        "camelcase": "off",
        "eqeqeq": "off",
        "func-names": "off",
        "guard-for-in": "off",
        "indent": ["error", 4],
        "max-len": "off",
        "no-alert": "off",
        "no-case-declarations": "off",
        "no-labels": "off",
        "no-param-reassign": "off",
        "no-restricted-globals": "off",
        "no-restricted-syntax": "off",
        "no-undef": "off",
        "no-unused-vars": "off",
        "no-use-before-define": "off",
        "no-var": "off"
    }
};