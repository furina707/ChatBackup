import subprocess
import shutil
from typing import List, Dict, Optional

class AdbClient:
    def __init__(self, port: int = 28888):
        self.port = port
        self.adb_path = shutil.which("adb")

    def is_available(self) -> bool:
        return self.adb_path is not None

    def get_devices(self) -> List[Dict[str, str]]:
        """获取当前已连接的设备列表"""
        if not self.is_available():
            return []
        try:
            result = subprocess.run(
                [self.adb_path, "devices", "-l"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            devices = []
            lines = result.stdout.strip().splitlines()
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    serial = parts[0]
                    state = parts[1]
                    info = " ".join(parts[2:]) if len(parts) > 2 else ""
                    devices.append({
                        "serial": serial,
                        "state": state,
                        "info": info
                    })
            return devices
        except Exception as e:
            return []

    def forward_port(self, serial: Optional[str] = None) -> bool:
        """建立本地端口映射: adb forward tcp:28888 tcp:28888"""
        if not self.is_available():
            return False
        cmd = [self.adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(["forward", f"tcp:{self.port}", f"tcp:{self.port}"])
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=5)
            return True
        except Exception:
            return False

    def remove_forward(self, serial: Optional[str] = None) -> bool:
        """移除端口映射"""
        if not self.is_available():
            return False
        cmd = [self.adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(["forward", "--remove", f"tcp:{self.port}"])
        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=5)
            return True
        except Exception:
            return False
