"""Minimal setup.py for local CLI installation."""

from setuptools import setup, find_packages

setup(
    name="smart-reviewer",
    version="0.1.0",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "PyGithub>=2.6.0",
        "litellm>=1.83.0",
        "Jinja2>=3.1.6",
        "PyYAML>=6.0.2",
        "tiktoken>=0.8.0",
        "pydantic>=2.10.6",
    ],
    entry_points={
        "console_scripts": [
            "smart-reviewer=smart_reviewer.cli:main",
        ],
    },
)
