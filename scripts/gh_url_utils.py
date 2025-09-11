#!/usr/bin/env python3
"""Shared utilities for generating GitHub URLs."""

import os
import subprocess
import sys


def get_github_base_url():
    """Get the appropriate GitHub base URL based on environment."""
    if os.getenv("README_ABSOLUTE_URLS"):
        try:
            result = subprocess.run(
                ["git", "describe", "--exact-match", "--tags", "HEAD"],
                capture_output=True, text=True, check=True
            )
            ref = result.stdout.strip()
            if not ref:
                print("ERROR: README_ABSOLUTE_URLS=1 but not on a tag", file=sys.stderr)
                sys.exit(1)
            return f"https://github.com/runsascoded/mdcmd/blob/{ref}"
        except subprocess.CalledProcessError:
            print("ERROR: README_ABSOLUTE_URLS=1 but not on a tag", file=sys.stderr)
            sys.exit(1)
    return None  # Use relative URLs


def format_url(path, base_url=None):
    """Format a URL as either absolute or relative."""
    if base_url:
        return f"{base_url}/{path}"
    return path