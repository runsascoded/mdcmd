from io import StringIO

from click import BadParameter, UsageError

from bmdf.cli import bmd, resolve_style

import pytest
parametrize = pytest.mark.parametrize


@parametrize(
    "args,envs,opts,expected",
    [
        (['echo', r'\$FOO=$FOO'], ['FOO=bar'], dict(shell=True), "# $FOO=bar\n"),
        (['echo', r'\$FOO=$FOO'], ['FOO=bar'], dict(shell=False), "# \\$FOO=$FOO\n"),
        (['seq', '10', '|', 'wc', '-l'], [], dict(shell=True), "# 10\n"),
        (['seq', '10', '|', 'wc', '-l'], [], dict(shell=False), "# 10\n"),
        (['seq', '10', '|', '$WC', '-l'], ['WC=wc'], dict(shell=True), "# 10\n"),
    ],
)
def test_env_vars(args, envs, opts, expected):
    file = StringIO()
    bmd.callback(
        args,
        env_strs=envs,
        **opts,
        file=file,
    )
    assert file.getvalue() == expected


@parametrize(
    "kwargs,expected",
    [
        (dict(style='comment'), [
            "# yay",
        ]),
        (dict(fence_level=0), [
            "# yay",
        ]),
        (dict(style='bash'), [
            "```bash",
            "echo yay",
            "# yay",
            "```",
        ]),
        (dict(fence_level=1), [
            "```bash",
            "echo yay",
            "# yay",
            "```",
        ]),
        (dict(style='split'), [
            "```bash",
            "echo yay",
            "```",
            "```",
            "yay",
            "```",
        ]),
        (dict(style='details'), [
            "<details><summary><code>echo yay</code></summary>",
            "",
            "```",
            "yay",
            "```",
            "</details>",
        ]),
        (dict(style='console'), [
            "```console",
            "$ echo yay",
            "yay",
            "```",
        ]),
        # `-f/--fence` and `-y/--style` agreeing is allowed
        (dict(style='bash', fence_level=1), [
            "```bash",
            "echo yay",
            "# yay",
            "```",
        ]),
        # Unique-prefix abbrev: "con" -> console
        (dict(style='con'), [
            "```console",
            "$ echo yay",
            "yay",
            "```",
        ]),
        # Unique-substring abbrev (no prefix matches): "sole" -> console
        (dict(style='sole'), [
            "```console",
            "$ echo yay",
            "yay",
            "```",
        ]),
        # `-t/--fence-type` overrides the `console` lang
        (dict(style='console', fence_type='shell-session'), [
            "```shell-session",
            "$ echo yay",
            "yay",
            "```",
        ]),
    ],
)
def test_styles(kwargs, expected):
    file = StringIO()
    bmd.callback(['echo', 'yay'], no_copy=True, file=file, **kwargs)
    assert file.getvalue().rstrip('\n').split('\n') == expected


@parametrize(
    "value,expected",
    [
        ('comment', 'comment'),
        ('b', 'bash'),
        ('sp', 'split'),
        ('d', 'details'),
        ('con', 'console'),
        ('sole', 'console'),
    ],
)
def test_resolve_style(value, expected):
    assert resolve_style(value) == expected


@parametrize(
    "value,matches",
    [
        ('co', ['comment', 'console']),   # ambiguous prefix
        ('a', ['bash', 'details']),       # ambiguous substring (no prefix matches)
    ],
)
def test_resolve_style_ambiguous(value, matches):
    with pytest.raises(BadParameter) as exc:
        resolve_style(value)
    assert str(matches) in str(exc.value)


def test_resolve_style_unknown():
    with pytest.raises(BadParameter, match="Unknown style 'zzz'"):
        resolve_style('zzz')


def test_style_fence_conflict():
    file = StringIO()
    with pytest.raises(UsageError, match=r"-f/--fence \(2x -> split\) conflicts with -y/--style \(console\)"):
        bmd.callback(['echo', 'yay'], no_copy=True, file=file, style='console', fence_level=2)
