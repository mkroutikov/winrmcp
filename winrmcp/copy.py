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
