from setuptools import setup

setup(
    name = 'pifaceio',
    py_modules = ['pifaceio'],
    version = '1.02',
    description = 'Simple interface for the Raspberry Pi PiFace board',
    long_description = open('README.md').read(),
    keywords = ['piface', 'spidev', 'raspberrypi'],
    classifiers = [],
    url = 'http://github.com/bulletmark/pifaceio',
    author = 'Mark Blakeney',
    author_email = 'blakeney.mark@gmail.com',
    license = 'GPLv3',
    install_requires = ['spidev'],
    scripts = ['install-spidev.sh'],
    zip_safe = False,
)
