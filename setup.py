#!/usr/bin/env python3
"""
Setup script for Rundeck ROI Plugin Manager
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="rundeck-roi-manager",
    version="1.0.0",
    author="ROI Plugin Team",
    description="Runbook Automation ROI Status - A tool to manage ROI metrics for Rundeck jobs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    py_modules=["main"],
    python_requires=">=3.7",
    install_requires=[
        "requests>=2.31.0",
        "certifi>=2025.4.26",
        "charset-normalizer>=3.4.2",
        "idna>=3.10",
        "urllib3>=2.4.0",
    ],
    entry_points={
        "console_scripts": [
            "rundeck-roi=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)