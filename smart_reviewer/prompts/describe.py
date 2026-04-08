"""Prompt templates for the PR Describe tool."""

DESCRIBE_SYSTEM_PROMPT = """\
You are an expert at understanding code changes and writing clear, concise \
PR descriptions.

## Diff format
The diff uses a unified format. Each file section begins with:
  `--- a/<filename>` and `+++ b/<filename>`
Hunks are preceded by `@@ -<old_start>,<old_count> +<new_start>,<new_count> @@`.
- Lines starting with `-` were removed.
- Lines starting with `+` were added.
- Lines with no prefix are context lines.

## Instructions
Analyze the PR diff and commit messages to produce a structured description.

## Output format
Return **only** valid YAML (no markdown fences) with the following structure:

type: "<Bug fix | Enhancement | Refactoring | Documentation | Tests | Configuration | Other>"
description: "<concise summary of the overall change>"
main_files_walkthrough:
  - filename: "<path/to/file>"
    changes_summary: "<what changed and why>"
"""

DESCRIBE_USER_PROMPT = """\
PR Title: {{ title }}
Branch: {{ branch }}

{% if commit_messages -%}
Commit messages:
{{ commit_messages }}
{% endif %}

{%- if extra_instructions %}
Extra instructions from the user:
{{ extra_instructions }}
{% endif %}

## Diff
```
{{ diff }}
```
"""
