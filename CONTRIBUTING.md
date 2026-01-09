# Contributors

# Reporting issues
* Describe (in detail) what should have happened. Include any supporting information (stack traces, errors, etc)
* Include any steps to replicate the issue
* Indicate OS and Python versions

# Development environment setup
1. Clone repository:
```
git clone https://github.com/mitre/caldera.git --recursive
```

2. Create a virtualenv:
```
python3 -m venv venv
. venv/bin/activate
```

3. Install dependencies:
```
pip install -r requirements.txt -r requirements-dev.txt
```

4. Install the pre-commit hooks:
```
pre-commit install --install-hooks
```

# Developing
We use the basic feature branch GIT flow. Fork this repository and create a feature branch off of master and when ready, submit a merge request. Make branch names and commits descriptive. A merge request should solve one problem, not many.

* Tests should cover any code changes that you have made. The test that you write should fail without your patch.
* [Run tests](#run-the-tests)

# Run the tests
Tests can be run by executing:
```
python -m pytest --asyncio-mode=auto
```
This will run all unit tests in your current development environment. Depending on the level of the change, you might need to run the test suite on various versions of Python. The unit testing pipeline will run the entire suite across multiple Python versions that we support when you submit your PR.

We utilize `tox` to test Caldera in multiple versions of Python. This will only run if the interpreter is present on your system. To run tox, execute:
```
tox
```

# Code Coverage
You can generate code coverage reports manually or by running `tox`. To run them manually, you must have `coverage` installed and run the following commands:
```
coverage run -m pytest
coverage report
coverage html
```
You can find the code coverage report in `htmlcov/index.html`