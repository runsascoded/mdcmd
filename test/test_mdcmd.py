from os.path import join, relpath
from tempfile import TemporaryDirectory

from click.testing import CliRunner
from utz import cd

from mdcmd.cli import main
from test.utils import DATA, ROOT


def test_mdcmd():
    with cd(ROOT):
        runner = CliRunner()
        with TemporaryDirectory() as tmpdir:
            in_path = join(DATA, 'README.md')
            out_path = join(tmpdir, 'README.md')
            res = runner.invoke(main, [in_path, out_path])
            assert res.exit_code == 0
            with (
                open(in_path, 'r', encoding='utf-8') as in_fd,
                open(out_path, 'r', encoding='utf-8') as out_fd,
            ):
                assert in_fd.read() == out_fd.read()


def test_mdcmd_command_failure():
    """Test that mdcmd exits with non-zero code when commands fail."""
    with cd(ROOT):
        runner = CliRunner()
        with TemporaryDirectory() as tmpdir:
            # Create a markdown file with a failing command
            in_path = join(tmpdir, 'test.md')
            out_path = join(tmpdir, 'output.md')
            with open(in_path, 'w') as f:
                f.write('# Test\n\n<!-- `false` -->\n```\nold\n```\n')

            res = runner.invoke(main, [in_path, out_path], catch_exceptions=False)
            assert res.exit_code == 1


def test_mdcmd_mixed_success_failure():
    """Test that mdcmd continues processing after failures and reports all errors."""
    with cd(ROOT):
        runner = CliRunner()
        with TemporaryDirectory() as tmpdir:
            in_path = join(tmpdir, 'test.md')
            out_path = join(tmpdir, 'output.md')
            with open(in_path, 'w') as f:
                f.write('''# Test

<!-- `echo "first"` -->
```
old
```

<!-- `false` -->
```
old
```

<!-- `echo "third"` -->
```
old
```
''')

            res = runner.invoke(main, [in_path, out_path], catch_exceptions=False)
            assert res.exit_code == 1

            # Verify successful commands still wrote output
            with open(out_path) as f:
                file_output = f.read()
                assert 'first' in file_output
                assert 'third' in file_output


def test_mdcmd_no_crash_on_error():
    """Test that mdcmd doesn't crash with traceback on command failure."""
    with cd(ROOT):
        runner = CliRunner()
        with TemporaryDirectory() as tmpdir:
            in_path = join(tmpdir, 'test.md')
            out_path = join(tmpdir, 'output.md')
            with open(in_path, 'w') as f:
                f.write('# Test\n\n<!-- `false` -->\n```\nold\n```\n')

            # Use catch_exceptions=True (default) to catch exceptions
            # If there's an uncaught exception, it will be in res.exception
            res = runner.invoke(main, [in_path, out_path])
            assert res.exit_code == 1
            # Should not have an uncaught exception
            assert res.exception is None or not isinstance(res.exception, Exception)
