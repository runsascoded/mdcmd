from __future__ import annotations

import asyncio
from asyncio import gather
import re
import shlex
from collections.abc import Coroutine
from contextlib import contextmanager
from functools import partial
from os import environ as env, rename, getcwd
from os.path import basename, exists, join
from tempfile import TemporaryDirectory
from typing import Any, Callable, Generator, Optional

from click import command, option, argument
from utz import err, Patterns, proc
from utz.cli import inc_exc, multi

from bmdf.utils import amend_opt, amend_check, amend_run, inplace_opt, no_cwd_tmpdir_opt

CMD_LINE_RGX = re.compile(r'<!-- `(?P<cmd>.+)` -->')
HTML_OPEN_RGX = re.compile(r'<(?P<tag>\w+)(?: +\w+(?:="[^"]*")?)* *>.*')
LINK_DEF_RGX = re.compile(r'^\[(?P<ref>[^\]]+)\]: (?P<url>.+)$')
Write = Callable[[str], None]

DEFAULT_FILE_ENV_VAR = 'MDCMD_DEFAULT_PATH'
DEFAULT_FILE = 'README.md'


async def async_text(cmd: str | list[str], env: dict | None = None) -> str:
    text = await proc.aio.text(cmd, env=env)
    return text.rstrip('\n')


async def async_line(arg: str) -> str:
    return arg


async def process_path(
    path: str,
    dry_run: bool,
    patterns: Patterns,
    write_fn: Write,
    concurrent: bool = True,
):
    blocks: list[Coroutine[None, None, str]] = []
    def write(arg: str | Coroutine[Any, Any, str]):
        blocks.append(async_line(arg) if isinstance(arg, str) else arg)

    with open(path, 'r') as fd:
        lines = map(lambda line: line.rstrip('\n'), fd)
        for line in lines:
            write(line)
            if not (m := CMD_LINE_RGX.match(line)):
                continue

            cmd_str = m.group('cmd')
            if patterns and not patterns(cmd_str):
                continue

            if dry_run:
                err(f"Would run: {cmd_str}")
                continue

            cmd = shlex.split(cmd_str)
            # Set environment variable for the current markdown file
            import os
            cmd_env = os.environ.copy()
            cmd_env['MDCMD_FILE'] = path

            is_link_def = False
            try:
                line = next(lines)
                if html_match := HTML_OPEN_RGX.fullmatch(line):
                    tag = html_match['tag']
                    close_lines = [f"</{tag}>"]
                elif line.startswith("```"):
                    if cmd[0] == "bmdff":
                        close_lines = ["```", re.compile(r"```\w+"), "```"]  # Skip two fences
                    else:
                        close_lines = ["```"]
                elif line.startswith("- "):
                    # Markdown list block - skip all list items
                    skip_lines = []
                    while line and (line.startswith("- ") or re.match(r"^ {2,}", line)):
                        skip_lines.append(line)
                        try:
                            line = next(lines)
                        except StopIteration:
                            break
                    close_lines = None
                elif LINK_DEF_RGX.match(line):
                    # Link definition block - skip until empty line or non-link-def line
                    is_link_def = True
                    close_lines = None
                elif not line:
                    close_lines = None
                else:
                    raise ValueError(f'Unexpected block start line under cmd {cmd}: {line}')
            except StopIteration:
                close_lines = None

            while close_lines:
                close, *close_lines = close_lines
                line = next(lines)
                while close.fullmatch(line) if isinstance(close, re.Pattern) else line != close:
                    line = next(lines)

            write(async_text(cmd, env=cmd_env))
            # Don't add blank line after link definitions
            if close_lines is None and not is_link_def:
                write("")

    if concurrent:
        gathered = await gather(*blocks)
        for line in gathered:
            write_fn(line)
    else:
        for block in blocks:
            line = await block
            write_fn(line)


@contextmanager
def out_fd(
    inplace: bool,
    path: str,
    out_path: Optional[str],
    dir: Optional[str] = None,
) -> Generator[Write, None, None]:
    if inplace:
        if out_path:
            raise ValueError('Cannot specify both --inplace and an output path')
        with TemporaryDirectory(dir=dir) as tmpdir:
            tmp_path = join(tmpdir, basename(path))
            with open(tmp_path, 'w') as f:
                yield partial(print, file=f)
            rename(tmp_path, path)
    else:
        if not out_path or out_path == '-':
            yield print
        else:
            with open(out_path, 'w') as f:
                yield partial(print, file=f)


@command('mdcmd')
@amend_opt
@option('-C', '--no-concurrent', is_flag=True, help='Run commands in sequence (by default, they are run concurrently)')
@inplace_opt
@option('-n', '--dry-run', is_flag=True, help="Print the commands that would be run, but don't execute them")
@no_cwd_tmpdir_opt
@inc_exc(
    multi('-x', '--execute', help='Only execute commands that match these regular expressions'),
    multi('-X', '--exclude', help="Only execute commands that don't match these regular expressions"),
)
@argument('path', required=False)
@argument('out_path', required=False)
def main(
    amend: bool,
    no_concurrent: bool,
    inplace: Optional[bool],
    dry_run: bool,
    no_cwd_tmpdir: bool,
    patterns: Patterns,
    path: str,
    out_path: Optional[str],
):
    """Parse a Markdown file, updating blocks preceded by <!-- `[cmd...]` --> delimiters.

    If no paths are provided, will look for a README.md, and operate "in-place" (same as ``mdcmd -i README.md``).
    """
    if not path:
        path = env.get(DEFAULT_FILE_ENV_VAR, DEFAULT_FILE)
        if not exists(path):
            raise ValueError(f'{path} not found')
        if inplace is None:
            inplace = True

    amend_check(amend)

    tmpdir = None if no_cwd_tmpdir else getcwd()
    with out_fd(inplace, path, out_path, dir=tmpdir) as write:
        asyncio.run(
            process_path(
                path=path,
                dry_run=dry_run,
                patterns=patterns,
                write_fn=write,
                concurrent=not no_concurrent,
            )
        )

    amend_run(amend)


if __name__ == '__main__':
    main()
