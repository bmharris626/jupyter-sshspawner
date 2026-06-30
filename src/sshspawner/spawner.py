"""JupyterHub spawner that launches single-user servers over SSH."""

import asyncssh
import os
import socket
import ipaddress
from textwrap import dedent
import random
import shutil
from tempfile import TemporaryDirectory
import shlex

from traitlets import Bool, Unicode, Integer, List, observe
from jupyterhub.spawner import Spawner


class SSHSpawner(Spawner):
    """Spawn Jupyter single-user servers on remote hosts via SSH."""

    remote_hosts = List(trait=Unicode(),
            help="Possible remote hosts from which to choose remote_host.",
            config=True)

    remote_host = Unicode("remote_host",
            help="SSH remote host to spawn sessions on")

    remote_ip = Unicode("remote_ip",
            help="IP on remote side")

    remote_port = Unicode("22",
            help="SSH remote port number",
            config=True)

    ssh_command = Unicode("/usr/bin/ssh",
            help="Actual SSH command",
            config=True)

    path = Unicode("",
            help="Default PATH (should include jupyter and python)",
            config=True)

    remote_port_command = Unicode("python3 -m sshspawner.get_port",
            help="Command to return unused port on remote host",
            config=True)

    local_logfile = Unicode("",
            help="Optional local debug logfile path. Empty disables file logging.",
            config=True)

    hub_api_url = Unicode("",
            help=dedent("""If set, Spawner will configure the containers to use
            the specified URL to connect the hub api. This is useful when the
            hub_api is bound to listen on all ports or is running inside of a
            container."""),
            config=True)

    ssh_keyfile = Unicode("~/.ssh/id_rsa",
            help=dedent("""Key file used to authenticate hub with remote host.

            `~` will be expanded to the user's home directory and `{username}`
            will be expanded to the user's username"""),
            config=True)

    strict_host_key_checking = Bool(True,
            help="Verify SSH host keys against known_hosts data.",
            config=True)

    ssh_known_hosts = Unicode("",
            help=("Optional known_hosts path. Empty uses asyncssh default "
                  "known_hosts lookup."),
            config=True)

    allow_loopback_no_host_key_checking = Bool(True,
            help=("If True, disable host key checking for loopback targets "
                  "(localhost/127.0.0.1) even when strict_host_key_checking is enabled."),
            config=True)

    pid = Integer(0,
            help=dedent("""Process ID of single-user server process spawned for
            current user."""))

    resource_path = Unicode(".jupyterhub-resources",
            help=dedent("""The base path where all necessary resources are
            placed. Generally left relative so that resources are placed into
            this base directory in the user's home directory."""),
            config=True)

    def load_state(self, state):
        """Restore state about ssh-spawned server after a hub restart.

        The ssh-spawned processes need IP and the process id."""
        super().load_state(state)
        if "pid" in state:
            self.pid = state["pid"]
        if "remote_ip" in state:
            self.remote_ip = state["remote_ip"]

    def get_state(self):
        """Save state needed to restore this spawner instance after hub restore.

        The ssh-spawned processes need IP and the process id."""
        state = super().get_state()
        if self.pid:
            state["pid"] = self.pid
        if self.remote_ip:
            state["remote_ip"] = self.remote_ip
        return state

    def clear_state(self):
        """Clear stored state about this spawner (ip, pid)"""
        super().clear_state()
        self.remote_ip = "remote_ip"
        self.pid = 0

    async def get_auth_credentials(self):
        """
        Fetch username and password from JupyterHub's auth_state.
        Returns (username, password)
        """
        username = self.user.name
        auth_state = await self.user.get_auth_state()
        if not auth_state or 'password' not in auth_state:
            raise RuntimeError("No password found in auth_state. Make sure your authenticator sets it!")
        password = auth_state['password']
        return username, password

    async def start(self):
        """Start single-user server on remote host."""
        username, password = await self.get_auth_credentials()

        self.remote_host = self.choose_remote_host()

        remote_ip, port = await self.remote_random_port()

        if remote_ip is None or port is None or port == 0:
            return False

        self.remote_ip = remote_ip
        self.port = port

        cmd = []
        cmd.extend(self.cmd)
        cmd.extend(self.get_args())

        port_found = False
        for index, value in enumerate(cmd):
            if value.startswith('--port'):
                cmd[index] = f'--port={port}'
                port_found = True
                break

        if not port_found:
            cmd.append(f'--port={port}')

        ip_found = False
        for index, value in enumerate(cmd):
            if value.startswith('--ip'):
                cmd[index] = '--ip=0.0.0.0'
                ip_found = True
                break

        if not ip_found:
            cmd.append('--ip=0.0.0.0')

        if self.user.settings.get("internal_ssl"):
            with TemporaryDirectory() as td:
                local_resource_path = td

                self.cert_paths = self.stage_certs(
                        self.cert_paths,
                        local_resource_path
                    )

                try:
                    async with asyncssh.connect(
                            self.remote_ip,
                            username=username,
                            password=password,
                            **self._ssh_connect_kwargs(self.remote_ip),
                    ) as conn:
                        mkdir_cmd = "mkdir -p {path} 2>/dev/null".format(path=self.resource_path)
                        result = await conn.run(mkdir_cmd)
                    files = [os.path.join(local_resource_path, f) for f in os.listdir(local_resource_path)]
                    async with asyncssh.connect(
                            self.remote_ip,
                            username=username,
                            password=password,
                            **self._ssh_connect_kwargs(self.remote_ip),
                    ) as conn:
                        await asyncssh.scp(files, (conn, self.resource_path))
                except asyncssh.PermissionDenied:
                    raise RuntimeError(
                        f"SSH authentication failed for {username} on {self.remote_ip}. "
                        "Check your password."
                    )
                except asyncssh.Error as e:
                    raise RuntimeError(f"SSH connection error during cert staging on {self.remote_ip}: {e}")

        if self.hub_api_url != "":
            old = "--hub-api-url={}".format(self.hub.api_url)
            new = "--hub-api-url={}".format(self.hub_api_url)
            for index, value in enumerate(cmd):
                if value == old:
                    cmd[index] = new

        remote_cmd = ' '.join(cmd)
        self.log.info(f"Starting server with command: {remote_cmd}")

        self._write_local_log(remote_cmd)

        self.pid = await self.exec_notebook(remote_cmd)

        self.log.debug("Starting User: {}, PID: {}".format(self.user.name, self.pid))

        if self.pid < 0:
            return None

        return (self.remote_ip, port)

    async def poll(self):
        """Poll ssh-spawned process to see if it is still running.

        If it is still running return None. If it is not running return exit
        code of the process if we have access to it, or 0 otherwise."""

        if not self.pid:
            self.clear_state()
            return 0

        alive = await self.remote_signal(0)
        self.log.debug("Polling returned {}".format(alive))

        if not alive:
            self.clear_state()
            return 0
        else:
            return None

    async def stop(self, now=False):
        """Stop single-user server process for the current user."""
        try:
            await self.remote_signal(15)
        except RuntimeError as e:
            self.log.warning("Could not signal process during stop (credentials unavailable?): %s", e)
        except asyncssh.Error as e:
            self.log.warning("SSH error during stop for %s: %s", self.user.name, e)
        self.clear_state()

    def get_remote_user(self, username):
        """Map JupyterHub username to remote username."""
        return username

    def choose_remote_host(self):
        """Choose a remote host from ``remote_hosts``."""
        return random.choice(self.remote_hosts)

    @observe('remote_host')
    def _log_remote_host(self, change):
        self.log.debug("Remote host was set to %s." % self.remote_host)

    @observe('remote_ip')
    def _log_remote_ip(self, change):
        self.log.debug("Remote IP was set to %s." % self.remote_ip)

    async def remote_random_port(self):
        """Select unoccupied port on the remote host and return it.

        If this fails for some reason return `None`."""

        username, password = await self.get_auth_credentials()
        try:
            async with asyncssh.connect(
                    self.remote_host,
                    username=username,
                    password=password,
                    **self._ssh_connect_kwargs(self.remote_host),
            ) as conn:
                result = await conn.run(self.remote_port_command)
        except asyncssh.PermissionDenied:
            raise RuntimeError(
                f"SSH authentication failed for {username} on {self.remote_host}. "
                "Check your password."
            )
        except asyncssh.Error as e:
            raise RuntimeError(f"SSH connection error on {self.remote_host}: {e}")
        stdout = result.stdout
        stderr = result.stderr
        retcode = result.exit_status

        if stdout and stdout.strip():
            try:
                ip, port = stdout.strip().split()
                port = int(port)
                self.log.debug("ip={} port={}".format(ip, port))
                return (ip, port)
            except (ValueError, IndexError) as e:
                self.log.error(f"Failed to parse port output: {stdout}. Error: {e}")
                return (None, None)
        else:
            self.log.error("Failed to get a remote port")
            self.log.error("STDERR={}".format(stderr))
            self.log.debug("EXITSTATUS={}".format(retcode))
            return (None, None)

    async def exec_notebook(self, command):
        """Start notebook server on remote host via SSH."""

        env = super(SSHSpawner, self).get_env()

        import json
        user_scopes = [f"access:servers!user={self.user.name}"]
        if self.user.admin:
            user_scopes.extend(["admin:users", "admin:servers"])

        env['JUPYTERHUB_USER_SCOPES'] = json.dumps(user_scopes)

        env['JUPYTERHUB_API_URL'] = self.hub_api_url if self.hub_api_url else self.hub.api_url
        if self.path:
            env['PATH'] = self.path
        username, password = await self.get_auth_credentials()
        bash_script_str = "#!/bin/bash\n"

        if self.local_logfile:
            lines = list(env)
            lines.append("------------------")
            lines.extend(super().get_env())
            self._write_local_log("\n".join(lines))

        for key, value in env.items():
            bash_script_str += f'export {key}=$(printf %s {shlex.quote(value)})\n'

        bash_script_str += 'unset XDG_RUNTIME_DIR\n'

        bash_script_str += 'touch .jupyter.log\n'
        bash_script_str += 'chmod 600 .jupyter.log\n'
        bash_script_str += '%s < /dev/null >> .jupyter.log 2>&1 & pid=$!\n' % command
        bash_script_str += 'echo $pid\n'

        self.log.debug("run script was written as:\n%s", bash_script_str)

        try:
            async with asyncssh.connect(
                    self.remote_ip,
                    username=username,
                    password=password,
                    **self._ssh_connect_kwargs(self.remote_ip),
            ) as conn:
                result = await conn.run("bash -s", input=bash_script_str)
        except asyncssh.PermissionDenied:
            raise RuntimeError(
                f"SSH authentication failed for {username} on {self.remote_ip}. "
                "Check your password."
            )
        except asyncssh.Error as e:
            raise RuntimeError(f"SSH connection error on {self.remote_ip}: {e}")
        stdout = result.stdout
        stderr = result.stderr
        retcode = result.exit_status

        self.log.debug("exec_notebook status={}".format(retcode))
        if stdout and stdout.strip():
            try:
                pid = int(stdout.strip())
                return pid
            except ValueError:
                self.log.error(f"Could not parse PID from: {stdout}")
                return -1
        else:
            self.log.error(f"No PID returned. stderr: {stderr}")
            return -1

    async def remote_signal(self, sig):
        """Signal on the remote host."""

        username, password = await self.get_auth_credentials()
        command = "kill -s %s %d < /dev/null"  % (sig, self.pid)

        try:
            async with asyncssh.connect(
                    self.remote_ip,
                    username=username,
                    password=password,
                    **self._ssh_connect_kwargs(self.remote_ip),
            ) as conn:
                result = await conn.run(command)
        except asyncssh.PermissionDenied:
            self.log.error("SSH authentication failed sending signal %s to %s", sig, self.remote_ip)
            return False
        except asyncssh.Error as e:
            self.log.error("SSH error sending signal %s to %s: %s", sig, self.remote_ip, e)
            return False
        stdout = result.stdout
        stderr = result.stderr
        retcode = result.exit_status
        self.log.debug("command: {} returned {} --- {} --- {}".format(command, stdout, stderr, retcode))
        return (retcode == 0)

    def stage_certs(self, paths, dest):
        """Move or copy cert files into a local staging directory.

        Parameters
        ----------
        paths : dict
            Mapping with ``keyfile``, ``certfile``, and ``cafile`` paths.
        dest : str
            Destination staging directory.

        Returns
        -------
        dict
            Mapping with remote cert file paths under ``self.resource_path``.
        """
        shutil.move(paths['keyfile'], dest)
        shutil.move(paths['certfile'], dest)
        shutil.copy(paths['cafile'], dest)

        key_base_name = os.path.basename(paths['keyfile'])
        cert_base_name = os.path.basename(paths['certfile'])
        ca_base_name = os.path.basename(paths['cafile'])

        key = os.path.join(self.resource_path, key_base_name)
        cert = os.path.join(self.resource_path, cert_base_name)
        ca = os.path.join(self.resource_path, ca_base_name)

        return {
            "keyfile": key,
            "certfile": cert,
            "cafile": ca,
        }

    def _write_local_log(self, content):
        """Write debug content to ``local_logfile`` when enabled."""
        if not self.local_logfile:
            return
        with open(self.local_logfile, "w") as fout:
            fout.write(content)

    def _ssh_connect_kwargs(self, host):
        """Build ``asyncssh.connect`` kwargs based on host-key policy."""
        if not self.strict_host_key_checking:
            return {"known_hosts": None}

        if self.allow_loopback_no_host_key_checking and self._is_loopback_host(host):
            return {"known_hosts": None}

        if self.ssh_known_hosts:
            return {"known_hosts": os.path.expanduser(self.ssh_known_hosts)}

        return {}

    def _is_loopback_host(self, host):
        """Return ``True`` if *host* resolves to loopback/local identity."""
        if not host:
            return False

        normalized = str(host).strip().lower()
        if normalized in {"localhost", "127.0.0.1", "::1"}:
            return True

        try:
            return ipaddress.ip_address(normalized).is_loopback
        except ValueError:
            pass

        local_names = {
            socket.gethostname().lower(),
            socket.getfqdn().lower(),
        }
        return normalized in local_names
