#!/usr/bin/env python3
"""Generate raw README.md link with dynamic line numbers.

Usage:
    python scripts/raw-readme-link.py mdcmd
    python scripts/raw-readme-link.py toc
    
Finds the relevant section in README.md and generates a link with line numbers.
When README_ABSOLUTE_URLS=1 is set, generates absolute GitHub URLs.
"""

import sys
from pathlib import Path

# Add current directory to path to import gh_url_utils
sys.path.insert(0, str(Path(__file__).parent))
from gh_url_utils import get_github_base_url, format_url


def find_readme_lines(section):
    """Find line numbers for the relevant section in README.md."""
    try:
        content = Path("README.md").read_text()
        lines = content.splitlines()
        
        # Map section names to their command patterns
        patterns = {
            "mdcmd": "<!-- `bmdf seq 3` -->",
            "toc": "<!-- `toc` -->"
        }
        
        if section not in patterns:
            return None
            
        pattern = patterns[section]
        
        # Find the pattern and determine the end based on content type
        for i, line in enumerate(lines, 1):
            if pattern in line:
                # For mdcmd example, find until closing ```
                if section == "mdcmd":
                    for j in range(i+1, len(lines)+1):
                        if j > len(lines) or lines[j-1] == "```":
                            return (i, j)
                # For toc, find until empty line
                else:
                    for j in range(i+1, len(lines)+1):
                        if j > len(lines):
                            return (i, j-1)
                        if not lines[j-1].strip():
                            return (i, j-1)
    except:
        pass
    return None


def main():
    """Generate the raw README link with line numbers."""
    if len(sys.argv) < 2:
        print("Usage: raw-readme-link.py {mdcmd|toc}", file=sys.stderr)
        sys.exit(1)
    
    section = sys.argv[1]
    if section not in ["mdcmd", "toc"]:
        print(f"Unknown section: {section}", file=sys.stderr)
        sys.exit(1)
    
    lines = find_readme_lines(section)
    base_url = get_github_base_url()
    
    # Build the path with line numbers
    if lines:
        start, end = lines
        readme_path = f"README.md?plain=1#L{start}-L{end}"
    else:
        readme_path = "README.md?plain=1"
    
    url = format_url(readme_path, base_url)
    
    # Generate the appropriate link text based on section
    print(f"[raw-{section}]: {url}")


if __name__ == "__main__":
    main()
