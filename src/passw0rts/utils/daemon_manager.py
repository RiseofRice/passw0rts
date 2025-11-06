"""
Daemon manager for running passw0rts web server as a background service
"""

import os
import sys
import platform
import subprocess
import signal
import time
from pathlib import Path
from typing import Optional

# Windows-specific imports (only available on Windows)
if platform.system() == 'Windows':
    try:
        # These may not be available on all Python installations
        CREATE_NEW_PROCESS_GROUP = subprocess.CREATE_NEW_PROCESS_GROUP
        DETACHED_PROCESS = subprocess.DETACHED_PROCESS
    except AttributeError:
        # Fallback values if not available
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        DETACHED_PROCESS = 0x00000008
else:
    CREATE_NEW_PROCESS_GROUP = None
    DETACHED_PROCESS = None


class DaemonManager:
    """Manages the passw0rts web server daemon"""

    def __init__(self):
        self.system = platform.system()
        self.pid_file = Path.home() / ".passw0rts" / "daemon.pid"
        self.log_file = Path.home() / ".passw0rts" / "daemon.log"

    def is_running(self) -> bool:
        """Check if the daemon is currently running"""
        if not self.pid_file.exists():
            return False

        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())

            # Check if process is actually running
            os.kill(pid, 0)  # Signal 0 doesn't kill, just checks if process exists
            return True
        except (OSError, ValueError):
            # Process doesn't exist or PID file is invalid
            self.pid_file.unlink(missing_ok=True)
            return False

    def get_pid(self) -> Optional[int]:
        """Get the PID of the running daemon"""
        if not self.pid_file.exists():
            return None

        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except (OSError, ValueError):
            return None

    def _kill_process(self, pid: int, force: bool = False):
        """
        Kill a process by PID.

        Args:
            pid: Process ID to kill
            force: If True, use SIGKILL/taskkill -F. If False, use SIGTERM/taskkill
        """
        if self.system == 'Windows':
            # Windows doesn't have SIGTERM, use taskkill
            subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                         capture_output=True, check=False)
        else:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)

    def start(self, host: str = '127.0.0.1', port: int = 5000, storage_path: Optional[str] = None):
        """Start the web server as a daemon"""
        if self.is_running():
            raise RuntimeError("Daemon is already running")

        # Ensure directory exists
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

        # Build command to start the web server
        cmd = [sys.executable, '-m', 'passw0rts.web.daemon',
               '--host', host, '--port', str(port)]

        if storage_path:
            cmd.extend(['--storage-path', storage_path])

        # Start daemon process
        if self.system == 'Windows':
            # Windows: Use CREATE_NEW_PROCESS_GROUP and DETACHED_PROCESS
            if CREATE_NEW_PROCESS_GROUP is not None and DETACHED_PROCESS is not None:
                creation_flags = CREATE_NEW_PROCESS_GROUP | DETACHED_PROCESS
            else:
                creation_flags = 0x00000200 | 0x00000008
            process = subprocess.Popen(
                cmd,
                stdout=open(self.log_file, 'a'),
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=creation_flags,
                close_fds=True
            )
        else:
            # Unix-like systems: Double fork to daemonize
            process = subprocess.Popen(
                cmd,
                stdout=open(self.log_file, 'a'),
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
                close_fds=True
            )

        # Save PID
        with open(self.pid_file, 'w') as f:
            f.write(str(process.pid))

        return process.pid

    def stop(self):
        """Stop the running daemon"""
        if not self.is_running():
            raise RuntimeError("Daemon is not running")

        pid = self.get_pid()
        if pid is None:
            raise RuntimeError("Could not determine daemon PID")

        # Send SIGTERM to gracefully shutdown
        try:
            self._kill_process(pid, force=False)

            # Wait a moment for graceful shutdown
            for _ in range(10):
                if not self.is_running():
                    break
                time.sleep(0.5)

            # Force kill if still running
            if self.is_running():
                self._kill_process(pid, force=True)

        finally:
            # Clean up PID file
            self.pid_file.unlink(missing_ok=True)

    def restart(self, host: str = '127.0.0.1', port: int = 5000, storage_path: Optional[str] = None):
        """Restart the daemon"""
        if self.is_running():
            self.stop()

        time.sleep(1)  # Brief pause before restart

        return self.start(host, port, storage_path)

    def get_logs(self, lines: int = 50) -> str:
        """Get the last N lines from the daemon log"""
        if not self.log_file.exists():
            return "No log file found"

        try:
            with open(self.log_file, 'r') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception as e:
            return f"Error reading log file: {e}"

    def install_service(self, host: str = '127.0.0.1', port: int = 5000,
                       storage_path: Optional[str] = None, auto_start: bool = True):
        """Install system service for automatic startup"""
        if self.system == 'Linux':
            return self._install_systemd_service(host, port, storage_path, auto_start)
        elif self.system == 'Darwin':
            return self._install_launchd_service(host, port, storage_path, auto_start)
        elif self.system == 'Windows':
            return self._install_windows_service(host, port, storage_path, auto_start)
        else:
            raise NotImplementedError(f"Service installation not supported on {self.system}")

    def uninstall_service(self):
        """Uninstall system service"""
        if self.system == 'Linux':
            return self._uninstall_systemd_service()
        elif self.system == 'Darwin':
            return self._uninstall_launchd_service()
        elif self.system == 'Windows':
            return self._uninstall_windows_service()
        else:
            raise NotImplementedError(f"Service uninstallation not supported on {self.system}")

    def _install_systemd_service(self, host: str, port: int,
                                 storage_path: Optional[str], auto_start: bool):
        """Install systemd service (Linux)"""
        service_name = "passw0rts-web"
        service_file = Path.home() / ".config" / "systemd" / "user" / f"{service_name}.service"

        # Create service file directory
        service_file.parent.mkdir(parents=True, exist_ok=True)

        # Build command
        cmd = f"{sys.executable} -m passw0rts.web.daemon --host {host} --port {port}"
        if storage_path:
            cmd += f" --storage-path {storage_path}"

        # Service file content
        service_content = f"""[Unit]
Description=Passw0rts Web Server
After=network.target

[Service]
Type=simple
ExecStart={cmd}
Restart=on-failure
RestartSec=10
StandardOutput=append:{self.log_file}
StandardError=append:{self.log_file}

[Install]
WantedBy=default.target
"""

        # Write service file
        service_file.write_text(service_content)

        # Reload systemd and enable service
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)

        if auto_start:
            subprocess.run(['systemctl', '--user', 'enable', service_name], check=True)
            subprocess.run(['systemctl', '--user', 'start', service_name], check=True)

        return str(service_file)

    def _uninstall_systemd_service(self):
        """Uninstall systemd service (Linux)"""
        service_name = "passw0rts-web"
        service_file = Path.home() / ".config" / "systemd" / "user" / f"{service_name}.service"

        # Stop and disable service
        subprocess.run(['systemctl', '--user', 'stop', service_name],
                      check=False, capture_output=True)
        subprocess.run(['systemctl', '--user', 'disable', service_name],
                      check=False, capture_output=True)

        # Remove service file
        service_file.unlink(missing_ok=True)

        # Reload systemd
        subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)

    def _install_launchd_service(self, host: str, port: int,
                                 storage_path: Optional[str], auto_start: bool):
        """Install launchd service (macOS)"""
        service_name = "com.passw0rts.web"
        plist_file = Path.home() / "Library" / "LaunchAgents" / f"{service_name}.plist"

        # Create directory
        plist_file.parent.mkdir(parents=True, exist_ok=True)

        # Build command arguments
        program_args = [sys.executable, '-m', 'passw0rts.web.daemon',
                       '--host', host, '--port', str(port)]
        if storage_path:
            program_args.extend(['--storage-path', storage_path])

        # Build program arguments XML
        args_xml = '\n'.join(f'        <string>{arg}</string>' for arg in program_args)

        # Plist file content
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{service_name}</string>
    <key>ProgramArguments</key>
    <array>
{args_xml}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    <key>StandardOutPath</key>
    <string>{self.log_file}</string>
    <key>StandardErrorPath</key>
    <string>{self.log_file}</string>
</dict>
</plist>
"""

        # Write plist file
        plist_file.write_text(plist_content)

        if auto_start:
            # Load the service
            subprocess.run(['launchctl', 'load', str(plist_file)], check=True)

        return str(plist_file)

    def _uninstall_launchd_service(self):
        """Uninstall launchd service (macOS)"""
        service_name = "com.passw0rts.web"
        plist_file = Path.home() / "Library" / "LaunchAgents" / f"{service_name}.plist"

        # Unload service
        subprocess.run(['launchctl', 'unload', str(plist_file)],
                      check=False, capture_output=True)

        # Remove plist file
        plist_file.unlink(missing_ok=True)

    def _install_windows_service(self, host: str, port: int,
                                 storage_path: Optional[str], auto_start: bool):
        """Install Windows service"""
        # For Windows, we'll use Task Scheduler instead of a full Windows Service
        # which requires pywin32 and more complexity

        task_name = "Passw0rtsWeb"

        # Build command
        cmd = f'"{sys.executable}" -m passw0rts.web.daemon --host {host} --port {port}'
        if storage_path:
            cmd += f' --storage-path "{storage_path}"'

        # Create scheduled task that runs at logon
        schtasks_cmd = [
            'schtasks', '/create', '/tn', task_name, '/tr', cmd,
            '/sc', 'onlogon', '/rl', 'limited', '/f'
        ]

        subprocess.run(schtasks_cmd, check=True, capture_output=True)

        if auto_start:
            # Run the task immediately
            subprocess.run(['schtasks', '/run', '/tn', task_name],
                          check=True, capture_output=True)

        return task_name

    def _uninstall_windows_service(self):
        """Uninstall Windows service"""
        task_name = "Passw0rtsWeb"

        # Delete scheduled task
        subprocess.run(['schtasks', '/delete', '/tn', task_name, '/f'],
                      check=False, capture_output=True)
