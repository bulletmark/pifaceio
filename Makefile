PYTHON = python

all:
	$(PYTHON) setup.py build

install:
	$(PYTHON) setup.py install

clean:
	$(PYTHON) setup.py clean
	rm -rf build dist *.egg-info *.egg *.pyc __pycache__
