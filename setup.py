import sys
from setuptools import setup, find_packages
from winrmcp import __version__, __description__, __author__, __author_email__, __url__


with open('README.md') as f:
    long_description = f.read()

setup(
    name        = 'winrmcp',
    version     = __version__,
    description = __description__,
    author      = __author__,
    author_email= __author_email__,
    long_description=long_description,
    long_description_content_type='text/markdown',
    url         = __url__,
    license     ='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=find_packages(),
    python_requires='>=3.6',
    install_requires=['pywinrm'],
    extras_require={  # from pywinrm's setup.py
        'credssp': ['requests-credssp>=1.0.0'],
        'kerberos:sys_platform=="win32"': ['winkerberos>=0.5.0'],
        'kerberos:sys_platform!="win32"': ['pykerberos>=1.2.1,<2.0.0']
    },
)
