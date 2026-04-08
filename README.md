# 🤖 Smart Reviewer

AI-powered pull request review, description, and improvement suggestions — available as a **local CLI tool** and a GitHub Action.

Smart Reviewer analyses your PR diff with a large-language model and posts
structured feedback directly on the pull request. It ships three tools that
can run automatically on every PR **or** on-demand via slash commands in
comments.

## Local CLI Usage

### Installation

```bash
pip install -r requirements.txt
pip install -e .
```

### Running

Set the required environment variables:

```bash
export GITHUB_TOKEN="your-github-token"
export OPENAI_API_KEY="your-openai-api-key"
```

Run against any GitHub pull request:

```bash
# Run all tools (review + describe + improve)
smart-reviewer https://github.com/owner/repo/pull/42

# Run specific tools only
smart-reviewer --review https://github.com/owner/repo/pull/42
smart-reviewer --describe --improve https://github.com/owner/repo/pull/42

# Print output to stdout only (don't post comments on the PR)
smart-reviewer --no-publish https://github.com/owner/repo/pull/42

# Override the LLM model
smart-reviewer --model gpt-3.5-turbo https://github.com/owner/repo/pull/42

# Enable verbose logging
smart-reviewer -v https://github.com/owner/repo/pull/42
```

You can also run it as a Python module:

```bash
python -m smart_reviewer https://github.com/owner/repo/pull/42
```

## GitHub Action Quick Start

Add the following workflow to `.github/workflows/smart-reviewer.yml`:

```yaml
name: Smart Reviewer
on:
  pull_request:
    types: [opened, synchronize, reopened]
  issue_comment:
    types: [created]

permissions:
  pull-requests: write
  issues: write
  contents: read

jobs:
  review:
    if: >
      github.event_name == 'pull_request' ||
      (github.event_name == 'issue_comment' &&
       contains(github.event.comment.body, '/review') ||
       contains(github.event.comment.body, '/describe') ||
       contains(github.event.comment.body, '/improve'))
    runs-on: ubuntu-latest
    steps:
      - uses: your-org/smart-reviewer@main
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          openai_api_key: ${{ secrets.OPENAI_API_KEY }}
```

## Configuration

| Input | Description | Default |
|-------|-------------|---------|
| `github_token` | GitHub token for API access | `${{ github.token }}` |
| `openai_api_key` | OpenAI (or compatible) API key | *required* |
| `model` | LLM model identifier (any model supported by [LiteLLM](https://docs.litellm.ai/)) | `gpt-4o` |
| `auto_review` | Run the review tool automatically on PR events | `true` |
| `auto_describe` | Run the describe tool automatically on PR events | `true` |
| `auto_improve` | Run the improve tool automatically on PR events | `true` |
| `extra_instructions` | Additional instructions appended to every prompt | `""` |

## Tools

### 🔍 `/review`
Performs a code review and posts:
- **Key issues** table with file, description, and line references
- **Effort estimation** badge (1-5 scale)
- **Security concerns** section

### 📝 `/describe`
Generates a structured PR description:
- PR type badge (Bug fix, Enhancement, Refactoring, …)
- Concise summary
- Files walkthrough table

### 💡 `/improve`
Suggests concrete code improvements:
- Existing vs. improved code diffs
- Actionable explanations for each suggestion

## Using Different LLM Providers

Smart Reviewer uses [LiteLLM](https://docs.litellm.ai/) under the hood, which
means you can point it at **any** supported provider by changing the `model`
input:

```yaml
# OpenAI (default)
model: gpt-4o

# Anthropic
model: anthropic/claude-3-opus-20240229

# Azure OpenAI
model: azure/my-deployment-name

# Amazon Bedrock
model: bedrock/anthropic.claude-3-sonnet-20240229-v1:0
```

Set the appropriate API key environment variable for your provider (e.g.
`ANTHROPIC_API_KEY`, `AZURE_API_KEY`) via repository secrets.

## Development

```bash
pip install -r requirements.txt
pytest
```

## License

MIT