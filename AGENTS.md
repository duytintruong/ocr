# Project
An app implementing OCR tasks.
Use Australian English for all documents, comments and variable names.

# Technical stack
- Cloud platform: AWS
    - AWS Profile: dius
    - AWS Region: ap-southeast-2
- Language: Python 3.14+
- LLM-Model: Amazon Bedrock au.anthropic.claude-sonnet-4-6
- Log: structlog
- CLI: fire (from google)

# Coding style and conventions
- Google Python coding style
- Use 4 spaces for indentation
- Type hints on all functions
- Docstrings on public functions
- .env.example committed, .env gitignored

# Development tools
- Package management: uv
- Command executions of python related packages: "uv run <command>"
- Linting, formating and sorting import libraries with ruff: "uv run ruff check --select I --fix ."
- Type checking with ty: "uv run ty"
- Testing
    - pytest

# Development process
- Plan first, then implement

# Project structure
- Source code: orc/
- Tests: tests/
- Documentation: docs/
- Configuration files: configs/
- The source code is packaged as a Python package using uv.
