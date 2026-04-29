# Contributing to Tostr
First off, thank you for considering contributing to Tostr!

Since Tostr is designed to be a robust infrastructure tool for optimizing LLM interactions, we aim to maintain a clean, strictly organized, and well-tested codebase. This document outlines the process for contributing to the project.

<!--
Table of Contents

- [Local Development Setup](#local-development-setup)

- [How to Contribute](#how-to-contribute)

- [Coding Standards & Architecture](#coding-standards-and-architecture)

- [Testing](#testing)

- [Pull Request Process](#pull-request-process)
-->

## Local Development Setup
To get your local environment set up for development:

1. **Fork the repository to your own GitHub account.**

2. **Clone your fork locally:**

```bash
git clone https://github.com/rubytanuki/Tostr.git
cd Tostr
```

**Set up a virtual environment (recommended) and install the dependencies:**

```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```
Verify your setup by running the existing test suite to ensure everything passes locally.

## How to Contribute
Please do not push directly to the `main` branch; we use a fork and PR workflow.

Check the **Issues** tab on GitHub. Look for anything labeled `good first issue`, `bug`, `feature`, etc.

If you want to work on an existing issue, leave a comment saying you are taking it so others know it's in progress.

If you want to build a new feature or fix a bug that isn't documented, open a new Issue first to discuss it before writing code.

Create a feature branch off of main for your work:

```bash
git checkout -b FEAT/your-feature-name
# or
git checkout -b FIX/your-bug-fix
# or
git checkout -b REFACTOR/your-refactor
```

## Coding Standards & Architecture
While Tostr is built in Python, we prefer to rein in Python's inherent "freedom" in favor of strict, predictable, and verbose architecture. It is better for maintainability to treat the codebase closer to how one might approach Java or C#.

When contributing, please adhere to the following:

- **Strict Type Hinting**: All function signatures and class properties must include type hints.

- **Object-Oriented Design**: Keep functions modular and encapsulated. Avoid floating helper functions if they belong inside a class handling a specific domain.

- **Verbose Naming**: Prefer descriptive variable and method names over abbreviated ones. `def calculate_token_reduction_percentage()` is always better than `def calc_tok_red()`.

- **Docstrings**: Every class and public method must have a docstring explaining its purpose, arguments, and return types.

## Testing
Before opening a Pull Request, ensure that your changes do not break existing functionality.

If you are adding a new feature (like a new language parser or an LLM API binding), write an automated test for it.

Run the test suite locally before pushing your code:
```bash
pytest run PLACEHOLDER
```

## Pull Request Process
1. Commit your changes locally. Write clear, descriptive commit messages.

2. Push your branch to your forked repository on GitHub.

3. Open a Pull Request (PR) against the main branch of the original repository.

4. In the PR description, link the issue you are solving by including `Closes #ISSUE_NUMBER`.

5. Wait for the automated CI/CD checks to pass. If they fail, review the logs, fix the issues locally, and push the updates to your branch.

6. A maintainer will review your code. We may request changes to ensure the code aligns with our architectural standards or quality threshold.

7. Once approved and all status checks pass, your PR will be merged! 🎉🎉
