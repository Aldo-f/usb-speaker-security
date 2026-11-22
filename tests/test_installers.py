import base64
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _write_mock_python(path, user_scripts):
    source = textwrap.dedent(
        f"""\
        #!{sys.executable}
        import os
        import pathlib
        import sys

        args = sys.argv[1:]
        if args == ["--version"]:
            print(f"Python {{sys.version_info.major}}.{{sys.version_info.minor}}.0")
        elif args == ["-m", "pip", "--version"]:
            print("pip 24.0")
        elif args[:3] == ["-m", "pip", "install"]:
            scripts = pathlib.Path(os.environ["FAKE_USER_SCRIPTS"])
            scripts.mkdir(parents=True, exist_ok=True)
            command = scripts / "usb-security"
            command.write_text("#!{sys.executable}\\nimport sys; sys.exit(0)\\n")
            command.chmod(0o755)
        elif args[:1] == ["-c"] and "sysconfig.get_path" in args[1]:
            print(os.environ["FAKE_USER_SCRIPTS"])
        else:
            print("unexpected mock Python arguments: " + repr(args), file=sys.stderr)
            sys.exit(2)
        """
    )
    path.write_text(source, encoding="utf-8")
    path.chmod(0o755)
    user_scripts.mkdir(parents=True, exist_ok=True)


def _run_unix_installer(tmp_path, shell_name, existing_profiles=()):
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("Bash is not installed")

    home = tmp_path / "home"
    fake_bin = tmp_path / "bin"
    user_scripts = home / ".local" / "bin"
    fake_bin.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    _write_mock_python(fake_bin / "python3", user_scripts)
    for profile in existing_profiles:
        (home / profile).write_text("# existing profile\n", encoding="utf-8")

    env = os.environ.copy()
    env.update(
        {
            "HOME": str(home),
            "PATH": str(fake_bin) + os.pathsep + env["PATH"],
            "SHELL": "/bin/" + shell_name,
            "FAKE_USER_SCRIPTS": str(user_scripts),
        }
    )
    result = subprocess.run(
        [bash, str(ROOT / "install.sh")],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return home, user_scripts, result.stdout


@pytest.mark.skipif(os.name != "posix", reason="Unix shell installer test")
def test_unix_installer_creates_profile_and_is_idempotent(tmp_path):
    home, user_scripts, first_output = _run_unix_installer(tmp_path, "bash")
    _, _, second_output = _run_unix_installer(tmp_path, "bash")

    profile = (home / ".profile").read_text(encoding="utf-8")
    path_line = f'export PATH="{user_scripts}:$PATH"'
    assert profile.count("# Added by usb-security installer") == 1
    assert profile.count(path_line) == 1
    assert f"Added {user_scripts} to {home / '.profile'}" in first_output
    assert "Added " not in second_output


@pytest.mark.skipif(os.name != "posix", reason="Unix shell installer test")
@pytest.mark.parametrize(
    ("shell_name", "selected_profile", "other_profile"),
    [
        ("bash", ".bashrc", ".profile"),
        ("zsh", ".zshrc", ".profile"),
    ],
)
def test_unix_installer_updates_active_shell_profile(
    tmp_path, shell_name, selected_profile, other_profile
):
    home, user_scripts, _ = _run_unix_installer(
        tmp_path, shell_name, (selected_profile, other_profile)
    )

    selected = (home / selected_profile).read_text(encoding="utf-8")
    other = (home / other_profile).read_text(encoding="utf-8")
    assert f'export PATH="{user_scripts}:$PATH"' in selected
    assert "# Added by usb-security installer" not in other


@pytest.mark.skipif(os.name != "nt", reason="Windows PATH persistence test")
def test_windows_installer_updates_process_and_user_path_independently(tmp_path):
    powershell = shutil.which("powershell")
    if not powershell:
        pytest.skip("Windows PowerShell is not installed")

    fake_modules = tmp_path / "modules"
    fake_pip = fake_modules / "pip"
    fake_pip.mkdir(parents=True)
    (fake_pip / "__init__.py").write_text("", encoding="utf-8")
    (fake_pip / "__main__.py").write_text(
        "import sys\n"
        "if sys.argv[1:] == ['--version']:\n"
        "    print('pip 24.0')\n"
        "elif sys.argv[1:2] != ['install']:\n"
        "    raise SystemExit('unexpected pip arguments: ' + repr(sys.argv[1:]))\n",
        encoding="utf-8",
    )

    env = os.environ.copy()
    installer_source = (ROOT / "install.ps1").read_text(encoding="utf-8")
    get_user_path = "[Environment]::GetEnvironmentVariable('PATH', 'User')"
    set_user_path = "Set-UserPath ($userEntries -join ';')"
    assert installer_source.count(get_user_path) == 2
    assert installer_source.count(set_user_path) == 1
    mock_installer = tmp_path / "install.ps1"
    mock_user_path_file = tmp_path / "user-path.txt"
    initial_user_path = r"C:\base\one;C:\base\two"
    mock_user_path_file.write_text(initial_user_path, encoding="utf-8")
    mock_installer.write_text(
        installer_source.replace(get_user_path, "$env:MOCK_USER_PATH").replace(
            set_user_path,
            "[System.IO.File]::WriteAllText($env:MOCK_USER_PATH_FILE, ($userEntries -join ';'))",
        ),
        encoding="utf-8",
    )
    env.update(
        {
            "PYTHONPATH": str(fake_modules),
            "PYTHONUSERBASE": str(tmp_path / "python-user-base"),
            "PATH": str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"],
            "INSTALLER": str(mock_installer),
            "MOCK_USER_PATH": initial_user_path,
            "MOCK_USER_PATH_FILE": str(mock_user_path_file),
        }
    )
    user_scripts = Path(
        subprocess.check_output(
            [
                sys.executable,
                "-c",
                "import sysconfig; print(sysconfig.get_path('scripts', sysconfig.get_preferred_scheme('user')))",
            ],
            env=env,
            text=True,
        ).strip()
    )
    user_scripts.mkdir(parents=True)
    env["FAKE_USER_SCRIPTS"] = str(user_scripts)
    script = r"""
        $ErrorActionPreference = 'Stop'
        $originalUserPath = $env:MOCK_USER_PATH
        $originalProcessPath = $env:PATH
        function Has-Path([string]$pathValue, [string]$target) {
            foreach ($entry in ($pathValue -split ';')) {
                if ($entry.TrimEnd('\') -ieq $target.TrimEnd('\')) { return $true }
            }
            return $false
        }
        function Count-Path([string]$pathValue, [string]$target) {
            return @($pathValue -split ';' | Where-Object {
                $_.TrimEnd('\') -ieq $target.TrimEnd('\')
            }).Count
        }
        try {
            $scripts = $env:FAKE_USER_SCRIPTS
            $withoutScripts = @($originalUserPath -split ';' | Where-Object {
                $_ -and -not (Has-Path $_ $scripts)
            })

            $env:MOCK_USER_PATH = ($withoutScripts -join ';')
            $env:PATH = "$scripts;$originalProcessPath"
            & $env:INSTALLER
            $env:MOCK_USER_PATH = [System.IO.File]::ReadAllText($env:MOCK_USER_PATH_FILE)
            if (-not (Has-Path $env:MOCK_USER_PATH $scripts)) {
                throw 'Installer did not add Scripts to the persistent user PATH.'
            }

            $env:MOCK_USER_PATH = (($withoutScripts + $scripts) -join ';')
            $env:PATH = $originalProcessPath
            & $env:INSTALLER
            if (-not (Has-Path $env:PATH $scripts)) {
                throw 'Installer did not add Scripts to the current process PATH.'
            }

            & $env:INSTALLER
            $env:MOCK_USER_PATH = [System.IO.File]::ReadAllText($env:MOCK_USER_PATH_FILE)
            if ((Count-Path $env:MOCK_USER_PATH $scripts) -ne 1) {
                throw 'Persistent user PATH contains duplicate Scripts entries.'
            }
        }
        finally {
            $env:MOCK_USER_PATH = $originalUserPath
            $env:PATH = $originalProcessPath
        }
    """
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    output_path = tmp_path / "powershell-output.txt"
    with output_path.open("w+", encoding="utf-8") as output:
        try:
            result = subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-NonInteractive",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-EncodedCommand",
                    encoded,
                ],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired as error:
            output.seek(0)
            raise AssertionError(
                f"Windows installer test timed out: {output.read()}"
            ) from error
        output.seek(0)
        output_text = output.read()
    assert result.returncode == 0, output_text
