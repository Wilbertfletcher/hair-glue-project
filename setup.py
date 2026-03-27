"""
Setup for Hair Glue Project Pipeline
"""

from setuptools import setup, find_packages

setup(
    name="hair-glue-pipeline",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "pyarrow",
        "duckdb",
    ],
    extras_require={
        "dev": ["pytest"],
    },
    entry_points={
        "console_scripts": [
            "pipeline-cli=pipeline.cli:main",
        ],
    },
)