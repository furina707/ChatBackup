import os
import re
import httpx
import time
from typing import Dict, Any, Optional, Callable, List

CURRENT_VERSION = "v1.0.0"
DEFAULT_REPO = "furina707/ChatBackup"

class UpdateInfo:
    def __init__(
        self,
        current_version: str,
        latest_version: str,
        has_update: bool,
        release_name: str,
        release_notes: str,
        published_at: str,
        html_url: str,
        assets: List[Dict[str, Any]]
    ):
        self.current_version = current_version
        self.latest_version = latest_version
        self.has_update = has_update
        self.release_name = release_name
        self.release_notes = release_notes
        self.published_at = published_at
        self.html_url = html_url
        self.assets = assets

def parse_version_tuple(v_str: str) -> tuple:
    """提取版本号数字，用于比较 v1.0.2 vs v1.0.1"""
    nums = re.findall(r"\d+", v_str)
    return tuple(map(int, nums)) if nums else (0,)

class SoftwareUpdater:
    def __init__(self, repo: str = DEFAULT_REPO):
        self.repo = repo
        self.current_version = CURRENT_VERSION

    def set_repo(self, repo: str):
        self.repo = repo.strip().strip("/")

    async def check_update(
        self,
        custom_api_url: Optional[str] = None
    ) -> UpdateInfo:
        """
        通过 HTTPS 检查最新版本
        支持 GitHub Releases API 或自定义 HTTPS JSON 规范
        """
        url = custom_api_url.strip() if custom_api_url else f"https://api.github.com/repos/{self.repo}/releases/latest"
        
        headers = {
            "User-Agent": f"ChatBackup-TUI/{self.current_version}",
            "Accept": "application/vnd.github.v3+json"
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, verify=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        latest_tag = data.get("tag_name") or data.get("version") or ""
        release_name = data.get("name") or latest_tag
        body = data.get("body") or "无更新日志说明"
        published_at = data.get("published_at") or ""
        html_url = data.get("html_url") or f"https://github.com/{self.repo}/releases"
        raw_assets = data.get("assets") or []

        assets = []
        for a in raw_assets:
            assets.append({
                "name": a.get("name", "release_asset"),
                "size": a.get("size", 0),
                "download_url": a.get("browser_download_url") or a.get("url"),
                "content_type": a.get("content_type", "")
            })

        curr_tup = parse_version_tuple(self.current_version)
        latest_tup = parse_version_tuple(latest_tag)
        has_update = latest_tup > curr_tup

        return UpdateInfo(
            current_version=self.current_version,
            latest_version=latest_tag or self.current_version,
            has_update=has_update,
            release_name=release_name,
            release_notes=body,
            published_at=published_at,
            html_url=html_url,
            assets=assets
        )

    async def download_asset(
        self,
        download_url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[int, int, float], None]] = None
    ) -> str:
        """
        通过安全 HTTPS 流式下载更新包
        progress_callback: (downloaded, total, speed_bytes_per_sec) -> None
        """
        os.makedirs(os.path.dirname(os.path.abspath(dest_path)), exist_ok=True)
        headers = {
            "User-Agent": f"ChatBackup-TUI/{self.current_version}"
        }

        async with httpx.AsyncClient(timeout=httpx.Timeout(600.0, connect=15.0), follow_redirects=True, verify=True) as client:
            async with client.stream("GET", download_url, headers=headers) as resp:
                resp.raise_for_status()
                total_bytes = int(resp.headers.get("content-length", 0))
                downloaded_bytes = 0
                start_time = time.time()
                last_time = start_time
                last_bytes = 0

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

        return dest_path
