# sshspawner

`sshspawner` is a JupyterHub spawner that launches single-user notebook servers on remote hosts over SSH.

It is useful when your Hub runs on one machine, but user servers should run on one or more separate Linux hosts.

## What It Does

- Chooses a target host from a configured host list.
- Asks the remote host for a free port (`python3 -m sshspawner.get_port` by default).
- Rewrites single-user startup args to enforce:
  - `--port=<selected-port>`
  - `--ip=0.0.0.0`
- Starts the single-user process remotely via `asyncssh`.

## Requirements

- Python `>=3.11`
- `jupyterhub`
- `asyncssh`
- `traitlets`

## Install

From source (this repo):

```bash
pip install .
```

Or for development:

```bash
pip install -e .
```

## JupyterHub Setup

Set the spawner class in your `jupyterhub_config.py`:

```python
c.JupyterHub.spawner_class = "sshspawner.SSHSpawner"

# Where user servers can be launched
c.SSHSpawner.remote_hosts = [
    "node1.example.lan",
    "node2.example.lan",
]

# Optional explicit remote SSH port (string trait)
c.SSHSpawner.remote_port = "22"

# Optional path override for single-user runtime
c.SSHSpawner.path = "/usr/local/bin:/usr/bin:/bin"
```

### Auth Requirement (Important)

`SSHSpawner` reads the remote SSH password from JupyterHub auth state:

- `await user.get_auth_state()` must return a dict containing `"password"`.

If your authenticator does not store this field, spawning will fail.

## Options Overview

Commonly used options:

- `c.SSHSpawner.remote_hosts` (list[str])
  - Candidate hosts to spawn onto.
- `c.SSHSpawner.remote_port` (str, default: `"22"`)
  - SSH TCP port on the target host.
- `c.SSHSpawner.remote_port_command` (str, default: `"python3 -m sshspawner.get_port"`)
  - Command run remotely to produce `"<ip> <port>"`.
- `c.SSHSpawner.path` (str, default: `""`)
  - If set, exported as `PATH` in the remote launch script.
- `c.SSHSpawner.local_logfile` (str, default: `""`)
  - Optional local debug file path; empty disables file writes.
- `c.SSHSpawner.hub_api_url` (str, default: `""`)
  - Override Hub API URL passed to user servers.
- `c.SSHSpawner.resource_path` (str, default: `".jupyterhub-resources"`)
  - Remote resource directory for staged cert files.

SSH host key policy:

- `c.SSHSpawner.strict_host_key_checking` (bool, default: `True`)
  - `True`: verify host keys.
  - `False`: disable host key verification (`known_hosts=None`).
- `c.SSHSpawner.ssh_known_hosts` (str, default: `""`)
  - Optional known-hosts file path when strict checking is enabled.
  - Empty string means AsyncSSH default known-hosts lookup.
- `c.SSHSpawner.allow_loopback_no_host_key_checking` (bool, default: `True`)
  - If enabled, loopback/self targets can bypass host key checks.

## Example: Localhost / Same-Node Hub + User Server

```python
c.JupyterHub.spawner_class = "sshspawner.SSHSpawner"
c.SSHSpawner.remote_hosts = ["localhost"]

# Keep strict checks for real remotes, but allow localhost carve-out
c.SSHSpawner.strict_host_key_checking = True
c.SSHSpawner.allow_loopback_no_host_key_checking = True
```

## Package Layout

- `src/sshspawner/spawner.py`: `SSHSpawner` implementation
- `src/sshspawner/get_port.py`: helper module that prints exactly `<ip> <port>`
- `get_port.py`: thin top-level wrapper for compatibility

## Notes and Behavior Contracts

- `remote_port_command` output format must remain exactly two fields: `<ip> <port>`.
- `start()` always enforces `--port` and `--ip=0.0.0.0` in the single-user command.
- Internal SSL cert staging uses `resource_path` on the remote host.

## Development

Run full verification:

```bash
make verify
```

Run tests only:

```bash
python3 -m unittest discover -s tests -v
```
