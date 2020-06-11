__version__ = '0.0.3'
__description__ = 'Package to execute commads on remote Windows, do file copy to the remote machine'
__author__ = 'Mike Kroutikov'
__author_email__ = 'mkroutikov@innodata.com'
__url__ = 'https://github.com/mkroutikov/winrmcp'


from .client import Client, Shell, ShellCommandError