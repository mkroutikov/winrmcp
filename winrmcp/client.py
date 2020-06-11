import winrm
import contextlib
import base64
import re
from .copy import do_copy
import xml.etree.ElementTree as ET


class Client(winrm.Session):

    @contextlib.contextmanager
    def shell(self):
        protocol = self.protocol
        shell_id = protocol.open_shell()

        try:
            yield Shell(protocol, shell_id)
        finally:
            protocol.close_shell(shell_id)

    def copy(self, from_file, to_file):
        if hasattr(from_file, 'read'):
            do_copy(self, from_file, to_file, max_operations_per_shell=15)
        else:
            with open(from_file, 'rb') as f:
                do_copy(self, f, to_file, max_operations_per_shell=15)


class Shell:
    def __init__(self, protocol, shell_id):
        self.protocol = protocol
        self.shell_id = shell_id

    def cmd(self, cmd, *args):
        command_id = self.protocol.run_command(self.shell_id, cmd, args)
        result = winrm.Response(self.protocol.get_command_output(self.shell_id, command_id))
        self.protocol.cleanup_command(self.shell_id, command_id)
        return result

    def check_cmd(self, cmd, *args):
        return self._check(self.cmd(cmd, *args))

    def ps(self, script):
        # must use utf16 little endian on windows
        encoded_ps = base64.b64encode(script.encode('utf_16_le')).decode('ascii')
        result = self.cmd('powershell', '-encodedcommand', encoded_ps)
        if len(result.std_err):
            # if there was an error message, clean it it up and make it human
            # readable
            result.std_err = _clean_error_msg(result.std_err)
        return result

    def check_ps(self, script):
        result = self.ps(script)
        return self._check(result)

    @staticmethod
    def _check(result):
        stdout = result.std_out.decode()
        stderr = result.std_err.decode() if result.std_err is not None else None
        if result.status_code != 0:
            raise ShellCommandError(result.status_code, stdout, stderr)
        return stdout, stderr


def _clean_error_msg(msg):
    """converts a Powershell CLIXML message to a more human readable string
    """
    # TODO prepare unit test, beautify code
    # if the msg does not start with this, return it as is
    if msg.startswith(b"#< CLIXML\r\n"):
        # for proper xml, we need to remove the CLIXML part
        # (the first line)
        msg_xml = msg[11:]
        try:
            # remove the namespaces from the xml for easier processing
            msg_xml = _strip_namespace(msg_xml)
            root = ET.fromstring(msg_xml)
            # the S node is the error message, find all S nodes
            nodes = root.findall("./S")
            new_msg = ""
            for s in nodes:
                # append error msg string to result, also
                # the hex chars represent CRLF so we replace with newline
                new_msg += s.text.replace("_x000D__x000A_", "\n")
        except Exception as e:
            # if any of the above fails, the msg was not true xml
            # print a warning and return the orignal string
            # TODO do not print, raise user defined error instead
            print("Warning: there was a problem converting the Powershell"
                    " error message: %s" % (e))
        else:
            # if new_msg was populated, that's our error message
            # otherwise the original error message will be used
            if len(new_msg):
                # remove leading and trailing whitespace while we are here
                return new_msg.strip().encode('utf-8')

def _strip_namespace(xml):
    """strips any namespaces from an xml string"""
    p = re.compile(b"xmlns=*[\"\"][^\"\"]*[\"\"]")
    allmatches = p.finditer(xml)
    for match in allmatches:
        xml = xml.replace(match.group(), b"")
    return xml

class ShellCommandError(RuntimeError):
    def __init__(self, status_code, stdout, stderr):
        self.status_code = status_code
        self.stdout = stdout
        self.stderr = stderr

        super().__init__(f'shell command failed, code={status_code}\n{stdout[:100]}\n{stderr[:100]}')


import uuid
import base64


def cleanup_content(shell, file_path : str):

    shell.check_ps(f'''
$tmp_file_path = [System.IO.Path]::GetFullPath("{file_path}")
if (Test-Path $tmp_file_path) {{
    Remove-Item $tmp_file_path -ErrorAction SilentlyContinue
}}''')


def restore_content(shell, from_path : str, to_path : str):
    shell.check_ps(f'''
$tmp_file_path = [System.IO.Path]::GetFullPath("{from_path}")
$dest_file_path = [System.IO.Path]::GetFullPath("{to_path}".Trim("'"))
if (Test-Path $dest_file_path) {{
    if (Test-Path -Path $dest_file_path -PathType container) {{
        Exit 1
    }} else {{
        rm $dest_file_path
    }}
}}
else {{
    $dest_dir = ([System.IO.Path]::GetDirectoryName($dest_file_path))
    New-Item -ItemType directory -Force -ErrorAction SilentlyContinue -Path $dest_dir | Out-Null
}}
if (Test-Path $tmp_file_path) {{
    $reader = [System.IO.File]::OpenText($tmp_file_path)
    $writer = [System.IO.File]::OpenWrite($dest_file_path)
    try {{
        for(;;) {{
            $base64_line = $reader.ReadLine()
            if ($base64_line -eq $null) {{ break }}
            $bytes = [System.Convert]::FromBase64String($base64_line)
            $writer.write($bytes, 0, $bytes.Length)
        }}
    }}
    finally {{
        $reader.Close()
        $writer.Close()
    }}
}} else {{
    echo $null > $dest_file_path
}}''')


def upload_chunks(shell, file_path : str, max_chunks : int, fileobj):
    # Upload the file in chunks to get around the Windows command line size limit.
    # Base64 encodes each set of three bytes into four bytes. In addition the output
    # is padded to always be a multiple of four.
    #
    #   ceil(n / 3) * 4 = m1 - m2
    #
    #   where:
    #     n  = bytes
    #     m1 = max (8192 character command limit.)
    #     m2 = len(filePath)

    chunk_size = ((8000 - len(file_path)) // 4) * 3

    if max_chunks == 0:
        max_chunks = 1

    for _ in range(max_chunks):
        chunk = fileobj.read(chunk_size)
        assert type(chunk) is bytes
        assert len(chunk) <= chunk_size

        if len(chunk) == 0:
            return True  # means "done"

        chunk = base64.b64encode(chunk).decode('ascii')
        shell.check_cmd(['echo', chunk, '>>', file_path])

    return False  # not yet done, just max_chunks exhausted


def do_copy(client, fileobj, to_path : str, max_operations_per_shell=0):
    temp_file = f'pywinrmcp-{uuid.uuid4()}.tmp'
    temp_path = f'$env:TEMP\\{temp_file}'

    try:
        while True:
            with client.shell() as shell:
                result = upload_chunks(shell, f'%TEMP%\\{temp_file}', max_operations_per_shell, fileobj)
                if result:
                    break
        with client.shell() as shell:
            restore_content(shell, temp_path, to_path)
    finally:
        with client.shell() as shell:
            cleanup_content(shell, temp_path)
