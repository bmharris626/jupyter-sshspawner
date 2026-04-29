# sshspawner

`sshspawner` is a JupyterHub spawner that starts single-user notebook servers on remote hosts over SSH.

## Requirements

- Python 3.11+
- `jupyterhub`
- `asyncssh`
- `traitlets`

## Package layout

- `src/sshspawner/spawner.py`: `SSHSpawner` implementation
- `src/sshspawner/get_port.py`: helper module that prints `<ip> <port>`
- `get_port.py`: wrapper script for local/module execution compatibility

## Runtime assumptions

- `auth_state` must include `password`; `SSHSpawner.get_auth_credentials()` requires it.
- `start()` enforces `--port=<selected_port>` and `--ip=0.0.0.0` in the single-user command.
- `remote_port_command` defaults to `python3 -m sshspawner.get_port` and expects stdout format `<ip> <port>`.
- SSH host key verification is controlled by `strict_host_key_checking` and `ssh_known_hosts`.
- Loopback targets can optionally bypass host key checks with `allow_loopback_no_host_key_checking`.

## Development

Run verification:

```bash
make verify
```

Run tests only:

```bash
make test
```
