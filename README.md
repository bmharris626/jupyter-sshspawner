# sshspawner

[![PyPI](https://img.shields.io/pypi/v/sshspawner.svg)](https://pypi.org/project/sshspawner/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A JupyterHub spawner that launches single-user notebook servers on remote hosts over SSH.

## Description

Useful when your JupyterHub runs on one machine but user servers should run on one or more separate Linux hosts. `sshspawner` chooses a target host from a configured list, finds a free port, rewrites single-user startup args to enforce `--port` and `--ip=0.0.0.0`, and starts the process remotely via `asyncssh`.

## Quick Start

```bash
pip install .
```

In your `jupyterhub_config.py`:

```python
c.JupyterHub.spawner_class = "sshspawner.SSHSpawner"
c.SSHSpawner.remote_hosts = ["node1.example.lan"]
```

Ensure your authenticator stores the user's SSH password in auth state (`await user.get_auth_state()["password"]`).

## Installation & Setup

### From source

```bash
pip install .
```

### Development

```bash
pip install -e .
```

### Prerequisites

- Python >= 3.11
- `jupyterhub`
- `asyncssh`
- `traitlets`

### Auth Requirement

`SSHSpawner` reads the remote SSH password from JupyterHub auth state. Your authenticator **must** store `"password"` in auth state, or spawning will fail.

## Usage

### Basic Configuration

```python
c.JupyterHub.spawner_class = "sshspawner.SSHSpawner"
c.SSHSpawner.remote_hosts = ["node1.example.lan", "node2.example.lan"]
```

### Localhost Example

```python
c.JupyterHub.spawner_class = "sshspawner.SSHSpawner"
c.SSHSpawner.remote_hosts = ["localhost"]
c.SSHSpawner.strict_host_key_checking = True
c.SSHSpawner.allow_loopback_no_host_key_checking = True
```

## Configuration Reference

| Setting | Type | Default | Description |
|---|---|---|---|
| `c.SSHSpawner.remote_hosts` | `list[str]` | *(required)* | Candidate hosts to spawn onto |
| `c.SSHSpawner.remote_port` | `str` | `"22"` | SSH TCP port on the target host |
| `c.SSHSpawner.remote_port_command` | `str` | `"python3 -m sshspawner.get_port"` | Command run remotely to produce `<ip> <port>` |
| `c.SSHSpawner.path` | `str` | `""` | If set, exported as `PATH` in the remote launch script |
| `c.SSHSpawner.local_logfile` | `str` | `""` | Optional local debug file path; empty disables file writes |
| `c.SSHSpawner.hub_api_url` | `str` | `""` | Override Hub API URL passed to user servers |
| `c.SSHSpawner.resource_path` | `str` | `".jupyterhub-resources"` | Remote resource directory for staged cert files |
| `c.SSHSpawner.strict_host_key_checking` | `bool` | `True` | Verify SSH host keys |
| `c.SSHSpawner.ssh_known_hosts` | `str` | `""` | Known-hosts file path when strict checking enabled |
| `c.SSHSpawner.allow_loopback_no_host_key_checking` | `bool` | `True` | Allow loopback targets to bypass host key checks |

## Project Structure

```
src/sshspawner/
  spawner.py          SSHSpawner implementation
  get_port.py         Helper module that prints <ip> <port>
  __init__.py         Package init, exports SSHSpawner
get_port.py           Thin top-level wrapper for compatibility
```

## Contributing

- Run tests: `python3 -m unittest discover -s tests -v`
- Run full verification: `make verify`
- Syntax check: `python3 -m py_compile get_port.py setup.py src/sshspawner/__init__.py src/sshspawner/spawner.py src/sshspawner/get_port.py`

## Changelog

No changelog is maintained. See the git history for release notes.

## License

MIT. See [LICENSE](LICENSE).
