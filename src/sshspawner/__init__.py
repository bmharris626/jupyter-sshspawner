__all__ = ["SSHSpawner"]


def __getattr__(name):
    if name == "SSHSpawner":
        from .spawner import SSHSpawner

        return SSHSpawner
    raise AttributeError(f"module 'sshspawner' has no attribute {name!r}")
