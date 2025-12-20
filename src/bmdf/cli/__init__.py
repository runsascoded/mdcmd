import shlex
import sys
from os import chdir
from subprocess import PIPE, Popen, CalledProcessError
from sys import stdout
from typing import Optional, Tuple, Any, IO

from click import argument, command, option, get_current_context, echo
from utz import env, proc
from utz.process import pipeline
from utz.process.cmd import Cmd

from bmdf import utils
from bmdf.utils import COPY_BINARIES, details, fence, quote

BMDF_ERR_FMT_VAR = 'BMDF_ERR_FMT'
BMDF_ERR_FMT = env.get(BMDF_ERR_FMT_VAR)
BMDF_ERR_FMT_HELP_STR = f' ("{BMDF_ERR_FMT}")' if BMDF_ERR_FMT else ''

BMDF_WORKDIR_VAR = 'BMDF_WORKDIR'

BMDF_SHELL_VAR = 'BMDF_SHELL'

BMDF_EXPANDUSER_VAR = 'BMDF_EXPANDUSER'

BMDF_EXPANDVARS_VAR = 'BMDF_EXPANDVARS'

BMDF_INCLUDE_STDERR_VAR = 'BMDF_INCLUDE_STDERR'


@command("fence", no_args_is_help=True)
@option('-A', '--strip-ansi', is_flag=True, help='Strip ANSI escape sequences from output')
@option('-C', '--no-copy', is_flag=True, help=f'Disable copying output to clipboard (normally uses first available executable from {COPY_BINARIES}')
@option('-e', '--error-fmt', default=BMDF_ERR_FMT, help=f'If the wrapped command exits non-zero, append a line of output formatted with this string. One "%d" placeholder may be used, for the returncode. Defaults to ${BMDF_ERR_FMT_VAR}{BMDF_ERR_FMT_HELP_STR}')
@option('-E', '--env', 'env_strs', multiple=True, help="k=v env vars to set, for the wrapped command")
@option('-f', '--fence', 'fence_level', count=True, help='Pass 0-3x to configure output style: 0x: print output lines, prepended by "# "; 1x: print a "```bash" fence block including the <command> and commented output lines; 2x: print a bash-fenced command followed by plain-fenced output lines; 3x: print a <details/> block, with command <summary/> and collapsed output lines in a plain fence.')
@option('-i/-I', '--include-stderr/--no-include-stderr', is_flag=True, default=None, help=f'Capture and interleave both stdout and stderr streams; falls back to ${BMDF_INCLUDE_STDERR_VAR}')
@option('-s/-S', '--shell/--no-shell', is_flag=True, default=None, help=f'Disable "shell" mode for the command; falls back to ${BMDF_SHELL_VAR}, but defaults to True if neither is set')
@option('-t', '--fence-type', help="When -f/--fence is 2 or 3, this customizes the fence syntax type that the output is wrapped in")
@option('-r', '--exit-code', type=int, default=None, help='Expected exit code; bmdf exits 0 if command exits with this code, non-zero otherwise (useful for diff commands that exit 1 on differences)')
@option('-u/-U', '--expanduser/--no-expanduser', is_flag=True, default=None, help=f'Pass commands through `os.path.expanduser` before `subprocess`; falls back to ${BMDF_EXPANDUSER_VAR}')
@option('-v/-V', '--expandvars/--no-expandvars', is_flag=True, default=None, help=f'Pass commands through `os.path.expandvars` before `subprocess`; falls back to ${BMDF_EXPANDVARS_VAR}')
@option('-w', '--workdir', help=f'`cd` to this directory before executing (falls back to ${BMDF_WORKDIR_VAR}')
@option('-x', '--executable', help="`shell_executable` to pass to Popen pipelines (default: $SHELL)")
@argument('command', required=True, nargs=-1)
def bmd(
    command: Tuple[str, ...],
    strip_ansi: bool = False,
    no_copy: bool = False,
    error_fmt: Optional[str] = None,
    env_strs: Tuple[str, ...] = (),
    fence_level: int = 0,
    include_stderr: bool = False,
    shell: Optional[bool] = None,
    fence_type: Optional[str] = None,
    exit_code: Optional[int] = None,
    expanduser: Optional[bool] = None,
    expandvars: Optional[bool] = None,
    workdir: Optional[str] = None,
    executable: Optional[str] = None,
    file: Optional[IO[Any]] = None,
):
    """Format a command and its output to markdown, either in a `bash`-fence or <details> block, and copy it to the clipboard."""
    if not command:
        ctx = get_current_context()
        echo(ctx.get_help())
        ctx.exit()

    if workdir is None:
        workdir = env.get(BMDF_WORKDIR_VAR)
    if workdir:
        chdir(workdir)

    if shell is None:
        shell = bool(env.get(BMDF_SHELL_VAR, True))

    if shell and executable is None:
        executable = env.get('SHELL')

    if command[0] == 'time':
        # Without `-p`, `time`'s output is not POSIX-compliant, doesn't get parsed properly
        if len(command) > 1 and not command[1].startswith('-'):
            command = [ command[0], '-p', *command[1:] ]

    env_opts = dict(
        kv.split('=', 1)
        for kv in env_strs
    )
    proc_env = { **env, **env_opts, }

    if expanduser is None:
        expanduser = env.get(BMDF_EXPANDUSER_VAR)

    if expandvars is None:
        expandvars = env.get(BMDF_EXPANDVARS_VAR)

    if include_stderr is None:
        include_stderr = env.get(BMDF_INCLUDE_STDERR_VAR, True)

    cmds: list[Cmd] = []
    start_idx = 0
    def mk_cmd(idx: int):
        nonlocal start_idx
        args = command[start_idx:idx]
        if shell:
            args = ' '.join([
                quote(arg)
                for arg in args
            ])
        cmd = Cmd.mk(
            args,
            **{
                'env': proc_env,
                'shell': shell,
                'expanduser': expanduser,
                'expandvars': expandvars,
                **(dict(executable=executable) if shell else {}),
            }
        )
        cmds.append(cmd)
        start_idx = idx + 1

    n = len(command)
    for idx, arg in enumerate(command):
        if arg == "|":
            mk_cmd(idx)
    if start_idx < n:
        mk_cmd(n)

    try:
        with env(env_opts):
            output = pipeline(cmds, both=include_stderr)
            returncode = 0
    except CalledProcessError as e:
        output = e.output
        if isinstance(output, bytes):
            output = output.decode()
        # When both=False (include_stderr=False), stderr is separate
        # Print it to stderr for debugging, but don't include in markdown output
        if not include_stderr and e.stderr:
            stderr = e.stderr
            if isinstance(stderr, bytes):
                stderr = stderr.decode()
            print(stderr, file=sys.stderr)
        returncode = e.returncode

    lines = [
        line.rstrip('\n')
        for line in
        output.split('\n')
    ]
    if lines and not lines[-1]:
        lines = lines[:-1]
    if returncode and error_fmt:
        try:
            error_line = error_fmt % returncode
        except TypeError:
            error_line = error_fmt
        lines.append(error_line)

    if len(cmds) == 1:
        cmd_str = shlex.join(command)
    else:
        cmd_str = " | ".join([ str(cmd) for cmd in cmds ])
    cmd_str = " ".join([
        *[
            f'"{env_str}"' if ' ' in env_str else env_str
            for env_str in env_strs
        ],
        cmd_str,
    ])

    out_lines = []

    def log(line=''):
        out_lines.append(utils.strip_ansi(line) if strip_ansi else line)

    def print_commented_lines():
        for line in lines:
            log(f'# {line}' if line else '#')

    def print_fenced_lines(typ: str = None):
        with fence(typ=typ, log=log):
            for line in lines:
                log(line)

    if not fence_level:
        print_commented_lines()
    elif fence_level == 1:
        with fence('bash', log=log):
            log(cmd_str)
            print_commented_lines()
    elif fence_level == 2:
        with fence('bash', log=log):
            log(cmd_str)
        print_fenced_lines(typ=fence_type)
    elif fence_level == 3:
        with details(code=cmd_str, log=log):
            print_fenced_lines(typ=fence_type)
    else:
        raise ValueError(f"Pass -f/--fence at most 3x")

    output = '\n'.join(out_lines)
    if not no_copy:
        copy_cmd = None
        for cmd in COPY_BINARIES:
            if proc.check('which', cmd, log=None):
                copy_cmd = cmd
                break
        if copy_cmd:
            p = Popen([copy_cmd], stdin=PIPE, stdout=PIPE, stderr=PIPE, text=True)
            p.communicate(input=output)

    file = file or stdout
    print(output, file=file)
    if exit_code is not None:
        # Expected exit code specified: exit 0 if it matches, 1 otherwise
        if returncode != exit_code:
            sys.exit(1)
    elif returncode != 0:
        sys.exit(returncode)


def bmd_f():
    sys.argv.insert(1, '-f')
    bmd()


def bmd_ff():
    sys.argv.insert(1, '-ff')
    bmd()


def bmd_fff():
    sys.argv.insert(1, '-fff')
    bmd()


if __name__ == '__main__':
    bmd()
