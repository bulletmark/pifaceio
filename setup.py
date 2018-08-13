import os, re
from setuptools import setup

here = os.path.dirname(os.path.abspath(__file__))
fullname = os.path.basename(here)
name = re.sub(r'-\d+\.\d+.*', '', fullname)
module = re.sub('-', '_', name)
readme = open(os.path.join(here, 'README.md')).read()

setup(
    name=name,
    py_modules=[module],
    version='1.26.3',
    description='Python interface to the Raspberry Pi PiFace board',
    long_description=readme,
    long_description_content_type="text/markdown",
    keywords=['piface', 'spidev', 'raspberrypi'],
    classifiers=[
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
    url='http://github.com/bulletmark/{}'.format(name),
    author='Mark Blakeney',
    author_email='blakeney.mark@gmail.com',
    license='GPLv3',
    include_package_data=True,
    zip_safe=False,
    scripts=[f for f in os.listdir(here)
        if os.path.isfile(f) and os.access(f, os.X_OK)]
)
