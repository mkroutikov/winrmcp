from winrmcp import Shell
from unittest.mock import Mock


def test_shell():
    protocol = Mock(
        get_command_output=Mock(return_value=(b'Hello', b'world!', 0))
    )
    shell = Shell(protocol, 33)

    out, err = shell.check_cmd('dir')
    assert out == 'Hello'
    assert err == 'world!'

