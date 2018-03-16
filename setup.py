from setuptools import setup

setup(
    name = 'pifaceio',
    py_modules = ['pifaceio'],
    version = '1.26.1',
    description = 'Python interface to the Raspberry Pi PiFace board',
    long_description = open('README.md').read(),
    long_description_content_type="text/markdown",
    keywords = ['piface', 'spidev', 'raspberrypi'],
    classifiers = [
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    url = 'http://github.com/bulletmark/pifaceio',
    author = 'Mark Blakeney',
    author_email = 'blakeney.mark@gmail.com',
    license = 'GPLv3',
    scripts = ['install-spidev.sh'],
    include_package_data = True,
    zip_safe = False,
)
