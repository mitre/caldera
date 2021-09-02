module.exports = {
    plugins: [
        "html",
        "jinja2"
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
        "comma-dangle": "off",
        "eqeqeq": "off",
        "func-names": "off",
        "guard-for-in": "off",
        "indent": ["error", 4],
        "max-len": "off",
        "newline-per-chained-call": "off",
        "no-alert": "off",
        "no-await-in-loop": "off",
        "no-case-declarations": "off",
        "no-console": "off",
        "no-labels": "off",
        "no-param-reassign": "off",
        "no-plusplus": "off",
        "no-restricted-globals": "off",
        "no-restricted-syntax": "off",
        "no-tabs": "off",
        "no-undef": "off",
        "no-unused-vars": "off",
        "no-use-before-define": "off",
        "no-useless-escape": "off",
        "no-var": "off",
        "object-shorthand": "off",
        "prefer-const": "off",
        "prefer-destructuring": "off"
    }
};