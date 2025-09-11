#!/usr/bin/env python3
"""Generate GitHub URLs for links in README.

Usage:
    # For a file link:
    python scripts/gh-url.py toc.py src/bmdf/toc.py
    
    # For a link with line numbers:
    python scripts/gh-url.py 'in CI' .github/workflows/ci.yml#L28-L31
    
When README_ABSOLUTE_URLS=1 is set, generates absolute GitHub URLs instead of
relative paths. This is used during PyPI package builds to ensure links work
correctly on PyPI's README display. Requires being on a git tag when this
environment variable is set.
"""

import sys
from pathlib import Path

# Add parent directory to path to import gh_url_utils
sys.path.insert(0, str(Path(__file__).parent))
from gh_url_utils import get_github_base_url, format_url


def main():
    """Generate the link definition."""
    if len(sys.argv) < 3:
        print("Usage: gh-url.py <link_text> <link_path>", file=sys.stderr)
        sys.exit(1)
    
    link_text = sys.argv[1]
    link_path = sys.argv[2]
    
    base_url = get_github_base_url()
    url = format_url(link_path, base_url)
    print(f"[{link_text}]: {url}")


if __name__ == "__main__":
    main()