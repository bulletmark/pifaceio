PYTHON = python

all:
	$(PYTHON) setup.py build

install:
	$(PYTHON) setup.py install

upload:
	$(PYTHON) setup.py sdist upload

clean:
	$(PYTHON) setup.py clean
	rm -rf build dist *.egg-info *.egg *.pyc __pycache__
