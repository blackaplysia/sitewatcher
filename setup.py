from glob import glob
from os.path import basename
from os.path import splitext

from setuptools import setup
from setuptools import find_packages

setup(
    name='sitewatcher',
    version='0.1.0',
    license='MIT LICENSE',
    description='Make sequential difference of references in a page',
    author='Miki Yutani',
    author_email='mkyutani@gmail.com',
    url='http://github.com/mkyutani/sitewatcher',
    packages=find_packages(),
    install_requires=open('requirements.txt').read().splitlines(),
    entry_points={
        'console_scripts': [
            'sitewatcher=app.sitewatcher:main',
        ]
    },
    zip_safe=False
)
