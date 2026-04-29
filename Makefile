PYTHON ?= python3

.PHONY: test verify

test:
	$(PYTHON) -m unittest discover -s tests -v

verify:
	$(PYTHON) -m py_compile get_port.py setup.py src/sshspawner/__init__.py src/sshspawner/spawner.py src/sshspawner/get_port.py tests/test_spawner.py tests/test_get_port.py
	$(PYTHON) -m unittest discover -s tests -v
