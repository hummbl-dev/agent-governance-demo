# Contributing to Agent Governance Demo

First off, thank you for considering contributing to this project! It's people like you that make it a great tool for the community.

## Collaboration with SINT Protocol
We are currently exploring a collaboration with the **SINT Protocol** to use this project as a reference backend for the SINT Python SDK. If you are interested in this effort, please see [Issue #1](https://github.com/hummbl-dev/agent-governance-demo/issues/1).

## Development Setup

1. Clone the repository
2. Install dependencies: `pip install -e ".[test]"`
3. Run tests: `python -m pytest`

## PR Process

1. Fork the repo and create your branch from `main`.
2. Ensure the test suite passes.
3. If you've added code that should be tested, add tests.
4. Ensure your code follows the existing style (we use `ruff` for linting).
5. Open a Pull Request!

## Code Style
We aim for zero-dependency, standard-library-only implementations. Please avoid adding third-party requirements to the `src/` directory.
