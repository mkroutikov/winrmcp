# winrmcp
<!-- [![Build Status](https://travis-ci.com/innodatalabs/redstork.svg?branch=master)](https://travis-ci.com/innodatalabs/redstork)
[![PyPI version](https://badge.fury.io/py/redstork.svg)](https://badge.fury.io/py/redstork)
[![Documentation Status](https://readthedocs.org/projects/red-stork/badge/?version=latest)](https://red-stork.readthedocs.io/en/latest/?badge=latest) -->

A Python library to execute remote commands on Windows (cmd.exe and PowerShell), and to transfer files.

This is a thin wrapper on top of excellent [pywinrm](https://github.com/diyan/pywinrm).

For file transfer, we use the same method as in Go package [winrmcp](https://github.com/packer-community/winrmcp).

## Installation
```bash
pip install winrmcp
```

## Quick start

```python
from winrmcp import Client

client = Client('my-windows-machine.com', auth=('CleverUser', 'cleverPassword'))

with client.shell() as shell:
    out, _ = shell.check_cmd(['ipconfig', '/all'])
    print(out)

    script = """$strComputer = $Host
    Clear
    $RAM = WmiObject Win32_ComputerSystem
    $MB = 1048576

    "Installed Memory: " + [int]($RAM.TotalPhysicalMemory /$MB) + " MB" """
    out, _ = shell.check_ps(script)
    print(out)

client.copy('/home/mike/temp/build.bat', '%TEMP%\\build.bat')
with client.shell() as shell:
    shell.check_call('cmd.exe', '/k', '%TEMP%\\build.bat)
```

## API

### Client

`Client` extends `winrm.Session` to provide `Client.shell` context-manager that opens remote shell.

See documentaiotn  of [pywinrm](https://github.com/diyan/pywinrm) for the expected parameters.

`Client.shell()` - creates a new context-managed shell, returns intsance of `Shell`.

`Client.copy(local_file, remote_file)` - copies the content of local file `local_file` to the remote machine as `remote_file`.
Note that `local_file` can be a file-like object, having `read` method returning `bytes`.

### Shell

`Shell` represent the shell running on the remote Windows machine. You can get an instance of this class by
calling `shell()` on a `Client` instance.

`Shell.cmd(command, *args)` - runs a command in remote `CMD.EXE` shell. Returns `winrm.Response` instance, see docs there.

`Shell.ps(script)` - runs a script in remote `PowerShell` shell. Returns `winrm.Response` instance, see docs there.

`Shell.check_cmd(command, *args)` - runs a command in remote `CMD.EXE` shell. Returns a tuple of stdout and stderr strings. If remote command
return non-zero code, raises `ShellCommandError` exception.

`Shell.check_ps(script)` - runs a script in remote `PowerShell` shell. Returns a tuple of stdout and stderr strings. If remote command
return non-zero code, raises `ShellCommandError` exception.
