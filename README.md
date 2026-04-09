# 🤖 Smart Reviewer

AI-powered pull request review, description, and improvement suggestions — a **local CLI tool**.

Smart Reviewer analyses your PR diff with a large-language model and
provides structured feedback. It ships three tools that you can run
from the command line against any GitHub pull request.

## Installation

```bash
pip install -r requirements.txt
pip install -e .
```

## Usage

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

## Configuration

Configuration is done via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `GITHUB_TOKEN` | GitHub personal access token | *required* |
| `OPENAI_API_KEY` | OpenAI (or compatible) API key | `""` (required for AI features) |
| `LLM_MODEL` | LLM model identifier (any model supported by [LiteLLM](https://docs.litellm.ai/)) | `gpt-4o` |
| `LLM_API_BASE` | Custom API base URL for self-hosted or corporate LLM endpoints | `""` |
| `MAX_TOKENS` | Maximum tokens for AI response | `4096` |
| `TEMPERATURE` | Sampling temperature | `0.2` |
| `EXTRA_INSTRUCTIONS` | Additional instructions appended to every prompt | `""` |
| `NUM_MAX_FINDINGS` | Maximum number of findings in the review | `3` |
| `REQUIRE_SECURITY_REVIEW` | Include security concerns section | `true` |
| `REQUIRE_EFFORT_ESTIMATION` | Include effort estimation badge | `true` |
| `GITHUB_API_URL` | GitHub API base URL for GitHub Enterprise Server | `""` (auto-detected) |
| `SSL_VERIFY` | Verify SSL certificates (set to `false` for corporate proxies) | `true` |

## Tools

### 🔍 `--review`
Performs a code review and outputs:
- **Key issues** table with file, description, and line references
- **Effort estimation** badge (1-5 scale)
- **Security concerns** section

### 📝 `--describe`
Generates a structured PR description:
- PR type badge (Bug fix, Enhancement, Refactoring, …)
- Concise summary
- Files walkthrough table

### 💡 `--improve`
Suggests concrete code improvements:
- Existing vs. improved code diffs
- Actionable explanations for each suggestion

## Using Different LLM Providers

Smart Reviewer uses [LiteLLM](https://docs.litellm.ai/) under the hood, which
means you can point it at **any** supported provider by changing the model:

```bash
# OpenAI (default)
smart-reviewer --model gpt-4o https://github.com/owner/repo/pull/42

# Anthropic
smart-reviewer --model anthropic/claude-3-opus-20240229 https://github.com/owner/repo/pull/42

# Azure OpenAI
smart-reviewer --model azure/my-deployment-name https://github.com/owner/repo/pull/42
```

Set the appropriate API key environment variable for your provider (e.g.
`ANTHROPIC_API_KEY`, `AZURE_API_KEY`).

## Corporate / Self-Hosted Setup

Smart Reviewer is designed to work on company laptops with restricted
internet access. You can point it at internal services instead of public
cloud APIs.

### GitHub Enterprise Server

If your organisation uses GitHub Enterprise Server, just pass the PR URL
as-is — the tool auto-detects the API endpoint from the hostname:

```bash
# Auto-detects https://github.example.com/api/v3
smart-reviewer https://github.example.com/myorg/myrepo/pull/10
```

You can also set an explicit API URL:

```bash
export GITHUB_API_URL="https://github.example.com/api/v3"
```

### Local / Self-Hosted LLM

Run a fully offline review with a local model (e.g. via
[Ollama](https://ollama.com)):

```bash
# Start Ollama locally
ollama serve

# Point Smart Reviewer at the local endpoint
export LLM_API_BASE="http://localhost:11434"
export LLM_MODEL="ollama/llama3"
export OPENAI_API_KEY="not-needed"

smart-reviewer --no-publish https://github.com/owner/repo/pull/42
```

Or point at any OpenAI-compatible internal endpoint:

```bash
export LLM_API_BASE="https://internal-llm.corp.com/v1"
export LLM_MODEL="gpt-4o"
smart-reviewer https://github.com/owner/repo/pull/42
```

### SSL / Corporate Proxy

If your company laptop uses a custom certificate authority or an
intercepting proxy, you may need to disable SSL verification:

```bash
export SSL_VERIFY=false
```

You can also set standard proxy environment variables which are honoured
by the underlying HTTP libraries:

```bash
export HTTPS_PROXY="http://proxy.corp.com:8080"
export HTTP_PROXY="http://proxy.corp.com:8080"
```

## Development

```bash
pip install -r requirements.txt
python -m pytest tests/ -v
```

## License

MIT