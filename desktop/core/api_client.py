import httpx
import os
import time
from typing import Dict, Any, Callable, Optional

class ApiClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 28888, timeout: float = 10.0):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    def set_host(self, host: str, port: int = 28888):
        self.base_url = f"http://{host}:{port}"

    async def get_status(self) -> Dict[str, Any]:
        """获取手机端服务状态"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/api/status")
            resp.raise_for_status()
            return resp.json()

    async def get_wechat_info(self) -> Dict[str, Any]:
        """获取微信账号与数据库元数据"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/api/wechat/info")
            resp.raise_for_status()
            return resp.json()

    async def get_qq_info(self) -> Dict[str, Any]:
        """获取QQ账号与数据库元数据"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/api/qq/info")
            resp.raise_for_status()
            return resp.json()

    async def download_file(
        self,
        endpoint: str,
        dest_path: str,
        progress_callback: Optional[Callable[[int, int, float], None]] = None
    ) -> bool:
        """
        流式下载大文件（例如数据库）
        progress_callback: (downloaded_bytes, total_bytes, speed_bytes_per_sec) -> None
        """
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        # 流式请求设置较长超时
        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=10.0)) as client:
            async with client.stream("GET", f"{self.base_url}{endpoint}") as resp:
                resp.raise_for_status()
                total_bytes = int(resp.headers.get("content-length", 0))
                downloaded_bytes = 0
                start_time = time.time()
                last_time = start_time
                last_bytes = 0
                speed = 0.0

                with open(dest_path, "wb") as f:
                    async for chunk in resp.aiter_bytes(chunk_size=65536):
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
                        
                        now = time.time()
                        if now - last_time >= 0.2:
                            speed = (downloaded_bytes - last_bytes) / (now - last_time)
                            last_bytes = downloaded_bytes
                            last_time = now
                            if progress_callback:
                                progress_callback(downloaded_bytes, total_bytes, speed)

                if progress_callback:
                    final_speed = downloaded_bytes / max(time.time() - start_time, 0.001)
                    progress_callback(downloaded_bytes, total_bytes, final_speed)
                return True
