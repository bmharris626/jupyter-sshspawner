"""Public package exports for sshspawner."""

__all__ = ["SSHSpawner"]


def __getattr__(name):
    """Lazily expose ``SSHSpawner`` to avoid import-time heavy deps."""
    if name == "SSHSpawner":
        from .spawner import SSHSpawner

        return SSHSpawner
    raise AttributeError(f"module 'sshspawner' has no attribute {name!r}")
