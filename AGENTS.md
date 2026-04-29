# Repository Notes

- This repo now uses a standard `src/` layout. The implementation lives in `src/sshspawner/spawner.py` and exports `SSHSpawner` from `src/sshspawner/__init__.py`.
- Packaging is defined by `pyproject.toml` (setuptools backend) with distribution name `sshspawner` and Python requirement `>=3.11`.
- `setup.py` is a compatibility shim (`setup()` only); project metadata should be edited in `pyproject.toml`.

# Entry Points

- `src/sshspawner/spawner.py`: defines `SSHSpawner`, the primary runtime code path.
- `src/sshspawner/get_port.py`: prints exactly `"<ip> <port>"` to stdout when run as a module. `SSHSpawner.remote_random_port()` splits stdout into two whitespace-separated fields, so changing this output format breaks spawning.
- `get_port.py`: thin wrapper script that calls `sshspawner.get_port.main()`.

# Runtime Constraints

- `SSHSpawner.get_auth_credentials()` requires `await self.user.get_auth_state()` to contain `password`. Any auth changes must preserve `auth_state['password']` or spawning fails.
- Remote connections currently use `asyncssh.connect(..., password=password, known_hosts=None)`. The `ssh_keyfile` trait exists but is not used by the implementation.
- `start()` rewrites/adds `--port=<chosen port>` and `--ip=0.0.0.0` in the single-user command before launching it remotely. Preserve that behavior when touching spawn flow.
- `remote_port_command` defaults to `python3 -m sshspawner.get_port`; remote environments must have `sshspawner` importable.
- Local debug file logging is optional via `local_logfile`; empty string disables local file writes.

# Safe Verification

- Use focused syntax checks: `python3 -m py_compile get_port.py setup.py src/sshspawner/__init__.py src/sshspawner/spawner.py src/sshspawner/get_port.py`.
- Run unit tests with: `python3 -m unittest discover -s tests -v`.
- `make verify` runs the syntax check + unit tests together.
- For packaging checks, use: `python3 setup.py --name` and `python3 setup.py --version`.

# Git Workflow Rule

- After each major repo change (feature, fix, refactor, packaging/update step), create a commit and push to `origin` (`n150:/git/jupyter-sshspawner.git`).
- Treat GitHub as secondary remote (`github`); do not push there unless explicitly requested.

# Non-Source Artifacts

- `dist/`, `*.egg-info/`, and `__pycache__/` are build artifacts.
- `jupyterhub.sqlite` is runtime state, not source.
