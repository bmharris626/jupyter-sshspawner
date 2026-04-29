# Repository Notes

- This repo is a single-module Python project. The real implementation is `sshspawner_didd.py`; `get_port.py` is the only helper script; `setup.py` is minimal packaging metadata.
- There is no repo-local README, CI workflow, test runner, linter, formatter, typechecker, or pre-commit config. Do not assume `pytest`, `ruff`, or similar commands are configured here.

# Entry Points

- `sshspawner_didd.py`: defines `SSHSpawner`, the only substantive code path.
- `get_port.py`: prints exactly `"<ip> <port>"` to stdout. `SSHSpawner.remote_random_port()` splits stdout into two whitespace-separated fields, so changing this output format breaks spawning.
- `setup.py`: package name is `sshspawner_didd`, but the code is still the top-level module file `sshspawner_didd.py`, not a package directory.

# Runtime Constraints

- `SSHSpawner.get_auth_credentials()` requires `await self.user.get_auth_state()` to contain `password`. Any auth changes must preserve `auth_state['password']` or spawning fails.
- Remote connections currently use `asyncssh.connect(..., password=password, known_hosts=None)`. The `ssh_keyfile` trait exists but is not used by the implementation.
- `start()` rewrites/adds `--port=<chosen port>` and `--ip=0.0.0.0` in the single-user command before launching it remotely. Preserve that behavior when touching spawn flow.
- The default `remote_port_command` is site-specific (`/jolts/.../get_port.py`). Treat `/jolts/...` paths and `/jolts/apps/jupyterhub/logs/sshSpawner.log` as deployment-specific assumptions, not portable paths.

# Safe Verification

- Use focused syntax checks instead of guessed test commands: `python -m py_compile sshspawner_didd.py get_port.py`.
- If you change packaging only, verify with `python setup.py --name` or `python setup.py --version`; avoid inventing a build pipeline that is not defined in the repo.

# Git Workflow Rule

- After each major repo change (feature, fix, refactor, packaging/update step), create a commit and push to `origin` (`n150:/git/jupyter-sshspawner.git`).
- Treat GitHub as secondary remote (`github`); do not push there unless explicitly requested.

# Non-Source Artifacts

- `dist/`, `sshspawner_didd.egg-info/`, and `__pycache__/` are build artifacts.
- `jupyterhub.sqlite` is runtime state, not source.
- `sshspawner_didd.py.bak` is a backup copy; prefer editing `sshspawner_didd.py` unless the user explicitly asks otherwise.
