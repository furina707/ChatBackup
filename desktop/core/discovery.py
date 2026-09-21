import asyncio
import json
import socket
from typing import Dict, Any, Callable, Optional

class DeviceDiscovery:
    """局域网 UDP 自动发现手机 Agent（免去任何 ADB 和数据线）"""
    def __init__(self, listen_port: int = 28889):
        self.listen_port = listen_port
        self.running = False
        self.loop = None
        self.transport = None

    class DiscoveryProtocol(asyncio.DatagramProtocol):
        def __init__(self, callback: Callable[[Dict[str, Any]], None]):
            self.callback = callback

        def datagram_received(self, data: bytes, addr: tuple):
            try:
                text = data.decode("utf-8")
                if text.startswith("CHAT_BACKUP_AGENT:"):
                    raw_json = text[len("CHAT_BACKUP_AGENT:"):]
                    info = json.loads(raw_json)
                    info["detected_ip"] = addr[0]
                    self.callback(info)
            except Exception:
                pass

    async def start_listen(self, on_device_found: Callable[[Dict[str, Any]], None]):
        """异步监听局域网设备广播"""
        self.running = True
        loop = asyncio.get_running_loop()
        try:
            # 绑定 UDP 端口监听
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(("", self.listen_port))
            sock.setblocking(False)

            self.transport, _ = await loop.create_datagram_endpoint(
                lambda: self.DiscoveryProtocol(on_device_found),
                sock=sock
            )
        except Exception as e:
            # 若端口被占用或受限，静默降级
            pass

    def stop(self):
        self.running = False
        if self.transport:
            self.transport.close()
            self.transport = None
