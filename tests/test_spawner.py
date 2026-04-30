"""Unit tests for sshspawner.spawner behavior."""

import importlib
import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"


def _install_test_stubs():
    """Install lightweight stubs for optional runtime dependencies."""
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))

    fake_asyncssh = types.ModuleType("asyncssh")

    class _FakeConnection:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def run(self, *_args, **_kwargs):
            return types.SimpleNamespace(stdout="", stderr="", exit_status=0)

    def _fake_connect(*_args, **_kwargs):
        return _FakeConnection()

    async def _fake_scp(*_args, **_kwargs):
        return None

    fake_asyncssh.connect = _fake_connect
    fake_asyncssh.scp = _fake_scp
    sys.modules["asyncssh"] = fake_asyncssh

    traitlets = types.ModuleType("traitlets")

    def _trait(*_args, **_kwargs):
        return None

    def _observe(*_args, **_kwargs):
        def _decorator(func):
            return func
        return _decorator

    traitlets.Bool = _trait
    traitlets.Unicode = _trait
    traitlets.Integer = _trait
    traitlets.List = _trait
    traitlets.observe = _observe
    traitlets.default = _observe
    sys.modules["traitlets"] = traitlets

    jupyterhub = types.ModuleType("jupyterhub")
    jupyterhub_spawner = types.ModuleType("jupyterhub.spawner")

    class FakeSpawner:
        def __init__(self):
            self.user = None
            self.cmd = []
            self._args = []
            self.port = 0
            self.hub = types.SimpleNamespace(api_url="http://hub:8081")
            self.log = types.SimpleNamespace(debug=lambda *_: None, info=lambda *_: None, error=lambda *_: None)

        def get_args(self):
            return list(self._args)

        def get_env(self):
            return {}

        def load_state(self, _state):
            return None

        def get_state(self):
            return {}

        def clear_state(self):
            return None

    jupyterhub_spawner.Spawner = FakeSpawner
    jupyterhub.spawner = jupyterhub_spawner
    sys.modules["jupyterhub"] = jupyterhub
    sys.modules["jupyterhub.spawner"] = jupyterhub_spawner


class SSHSpawnerTests(unittest.IsolatedAsyncioTestCase):
    """Behavioral tests for ``SSHSpawner`` helper and start logic."""

    @classmethod
    def setUpClass(cls):
        _install_test_stubs()
        cls.spawner_module = importlib.import_module("sshspawner.spawner")

    def _new_spawner(self):
        spawner = self.spawner_module.SSHSpawner()

        async def _auth_state():
            return {"password": "secret"}

        spawner.user = types.SimpleNamespace(
            name="alice",
            admin=False,
            settings={},
            get_auth_state=_auth_state,
        )
        return spawner

    async def test_get_auth_credentials_requires_password(self):
        spawner = self._new_spawner()

        async def _bad_auth_state():
            return {}

        spawner.user = types.SimpleNamespace(
            name="alice",
            admin=False,
            settings={},
            get_auth_state=_bad_auth_state,
        )

        with self.assertRaises(RuntimeError):
            await spawner.get_auth_credentials()

    async def test_remote_random_port_parses_ip_port(self):
        spawner = self._new_spawner()
        spawner.remote_host = "node1"
        spawner.remote_port_command = "ignored"

        class FakeConn:
            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def run(self, _cmd):
                return types.SimpleNamespace(stdout="127.0.0.1 43123\n", stderr="", exit_status=0)

        self.spawner_module.asyncssh.connect = lambda *_args, **_kwargs: FakeConn()

        ip, port = await spawner.remote_random_port()
        self.assertEqual(ip, "127.0.0.1")
        self.assertEqual(port, 43123)

    async def test_start_enforces_ip_and_port_args(self):
        spawner = self._new_spawner()
        spawner.cmd = ["jupyterhub-singleuser"]
        spawner._args = ["--ip=127.0.0.1", "--port=9999", "--debug"]
        spawner.remote_hosts = ["node1"]
        spawner.choose_remote_host = lambda: "node1"

        async def _fake_remote_random_port():
            return ("10.0.0.5", 22334)

        captured = {}

        async def _fake_exec_notebook(command):
            captured["command"] = command
            return 1234

        spawner.remote_random_port = _fake_remote_random_port
        spawner.exec_notebook = _fake_exec_notebook

        result = await spawner.start()

        self.assertEqual(result, ("10.0.0.5", 22334))
        self.assertIn("--port=22334", captured["command"])
        self.assertIn("--ip=0.0.0.0", captured["command"])
        self.assertNotIn("--port=9999", captured["command"])
        self.assertNotIn("--ip=127.0.0.1", captured["command"])

    async def test_start_handles_remote_port_failure_without_trait_error(self):
        spawner = self._new_spawner()
        spawner.remote_hosts = ["node1"]
        spawner.choose_remote_host = lambda: "node1"
        spawner.remote_ip = "remote_ip"

        async def _failed_remote_random_port():
            return (None, None)

        spawner.remote_random_port = _failed_remote_random_port

        result = await spawner.start()
        self.assertFalse(result)
        self.assertEqual(spawner.remote_ip, "remote_ip")

    async def test_ssh_known_hosts_policy(self):
        spawner = self._new_spawner()

        spawner.strict_host_key_checking = True
        spawner.allow_loopback_no_host_key_checking = True
        spawner.ssh_known_hosts = ""
        self.assertEqual(spawner._ssh_connect_kwargs("localhost"), {"known_hosts": None})
        self.assertEqual(spawner._ssh_connect_kwargs("192.168.2.10"), {})

        spawner.ssh_known_hosts = "~/.ssh/known_hosts"
        kwargs = spawner._ssh_connect_kwargs("192.168.2.10")
        self.assertIn("known_hosts", kwargs)
        self.assertTrue(kwargs["known_hosts"].endswith("/.ssh/known_hosts"))

        spawner.strict_host_key_checking = False
        self.assertEqual(spawner._ssh_connect_kwargs("192.168.2.10"), {"known_hosts": None})


if __name__ == "__main__":
    unittest.main()
