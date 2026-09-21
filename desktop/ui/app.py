import asyncio
import os
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header, Footer, Button, Label, Input, ProgressBar, RichLog, TabbedContent, TabPane, 
    DataTable, Static, ListItem, ListView
)
from textual.binding import Binding

from desktop.core.discovery import DeviceDiscovery
from desktop.core.adb_client import AdbClient
from desktop.core.api_client import ApiClient
from desktop.core.wechat_crypto import compute_wechat_key, WeChatDatabase, decrypt_wechat_db
from desktop.core.qq_parser import QqDatabase
from desktop.core.exporter import ChatExporter

class ChatBackupApp(App):
    CSS = """
    Screen {
        background: #0d1117;
        color: #e6edf3;
    }
    TabbedContent {
        height: 100%;
    }
    .panel {
        background: #161b22;
        border: solid #30363d;
        padding: 1 2;
        margin: 1;
        border-radius: 1;
    }
    .status-badge-ok {
        color: #3fb950;
        text-style: bold;
    }
    .status-badge-err {
        color: #f85149;
        text-style: bold;
    }
    .title-label {
        text-style: bold;
        color: #58a6ff;
        margin-bottom: 1;
    }
    #left-panel {
        width: 32%;
        border-right: solid #30363d;
        padding: 1;
    }
    #right-panel {
        width: 68%;
        padding: 1;
    }
    .msg-bubble-sent {
        background: #238636;
        color: #ffffff;
        margin: 1 0 1 10;
        padding: 1 2;
        border-radius: 1;
    }
    .msg-bubble-recv {
        background: #21262d;
        color: #e6edf3;
        margin: 1 10 1 0;
        padding: 1 2;
        border-radius: 1;
        border: solid #30363d;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "退出"),
    ]

    def __init__(self):
        super().__init__()
        self.adb = AdbClient()
        self.api = ApiClient()
        self.discovery = DeviceDiscovery()
        self.output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.current_wechat_db: str = ""
        self.current_qq_db: str = ""
        self.active_messages = []
        self.current_talker = ""
        self.current_talker_name = ""
        self.discovered_devices = {}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with TabbedContent(initial="tab-conn"):
            # Tab 1: 局域网纯无线免 ADB 交互
            with TabPane("1. 无线连接与设备 (免ADB)", id="tab-conn"):
                with Horizontal():
                    with Vertical(classes="panel", id="wireless-panel"):
                        yield Label("局域网自动发现 (无需USB线 / 无需ADB)", classes="title-label")
                        yield Label("手机 App 开启服务后将自动显示在此处：")
                        yield DataTable(id="discovered-table")
                        with Horizontal():
                            yield Button("选中设备一键连接", id="btn-connect-discovered", variant="success")
                            yield Button("刷新搜索", id="btn-refresh-scan", variant="default")

                    with Vertical(classes="panel", id="manual-panel"):
                        yield Label("手动 IP 连接 / 状态", classes="title-label")
                        with Horizontal():
                            yield Label("手机 IP:")
                            yield Input(value="192.168.1.2", id="input-ip", placeholder="查看手机App显示的IP")
                            yield Label("端口:")
                            yield Input(value="28888", id="input-port", placeholder="28888")
                        yield Button("直接测试连接", id="btn-manual-connect", variant="primary")
                        yield Static("等待连接...", id="agent-status-box")
                        
                        with Vertical(classes="panel", id="adb-fallback"):
                            yield Label("（备用）有线 ADB 模式", classes="title-label")
                            yield Button("一键 ADB Forward 转发 (备用)", id="btn-adb-fallback", variant="default")

            # Tab 2: 备份与解密同步
            with TabPane("2. 数据同步与解密", id="tab-sync"):
                with Vertical(classes="panel"):
                    yield Label("一键提取与解密控制台", classes="title-label")
                    with Horizontal():
                        yield Button("拉取并解密微信数据", id="btn-sync-wechat", variant="success")
                        yield Button("拉取 QQ 数据库", id="btn-sync-qq", variant="primary")
                    yield Label("传输进度：", id="lbl-progress")
                    yield ProgressBar(id="sync-progress", show_percentage=True, show_eta=True)
                    yield RichLog(id="sync-log", highlight=True, markup=True)

            # Tab 3: 聊天记录浏览器
            with TabPane("3. 聊天浏览器", id="tab-explore"):
                with Horizontal():
                    with Vertical(id="left-panel"):
                        yield Label("好友与群聊列表", classes="title-label")
                        yield Input(placeholder="过滤联系人...", id="input-filter-contacts")
                        yield ListView(id="contacts-list")
                    with Vertical(id="right-panel"):
                        with Horizontal():
                            yield Label("消息内容流", id="chat-title", classes="title-label")
                            yield Button("导出当前会话为 HTML", id="btn-export-html", variant="warning")
                            yield Button("导出当前会话为 CSV", id="btn-export-csv", variant="default")
                        yield VerticalScroll(id="chat-messages-container")

        yield Footer()

    async def on_mount(self) -> None:
        table = self.query_one("#discovered-table", DataTable)
        table.add_columns("设备名称/型号", "局域网 IP", "端口", "通信方式")
        # 启动 UDP 局域网无感自动发现
        await self.discovery.start_listen(self._on_device_discovered)

    def _on_device_discovered(self, info: dict):
        """收到手机 App 发来的局域网广播包"""
        ip = info.get("detected_ip") or info.get("ip")
        if not ip:
            return
        model = info.get("device_model", "Android Device")
        port = info.get("port", 28888)
        
        table = self.query_one("#discovered-table", DataTable)
        if ip not in self.discovered_devices:
            self.discovered_devices[ip] = info
            table.add_row(model, ip, str(port), "无线 Wi-Fi 直连", key=ip)
            # 自动把 IP 填入输入框
            self.query_one("#input-ip", Input).value = ip

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        log = self.query_one("#sync-log", RichLog)

        if btn_id in ("btn-connect-discovered", "btn-manual-connect"):
            ip = self.query_one("#input-ip", Input).value.strip()
            port = int(self.query_one("#input-port", Input).value.strip() or 28888)
            self.api.set_host(ip, port)
            status_box = self.query_one("#agent-status-box", Static)
            try:
                status_box.update(f"正在直连手机端 {ip}:{port}...")
                res = await self.api.get_status()
                device_model = res.get("device_model", "Unknown")
                is_root = res.get("has_root", False)
                root_text = "[green]已获得 SukiSU Root 权限[/green]" if is_root else "[yellow]未获取Root[/yellow]"
                status_box.update(f"[bold green]✔ 无线直连成功！[/bold green]\n设备: {device_model}\n{root_text}\n传输方式: 纯网络/免数据线")
            except Exception as e:
                status_box.update(f"[red]✘ 连接失败: {str(e)}[/red]\n请确认手机与电脑在同一Wi-Fi，且手机App已开启服务")

        elif btn_id == "btn-adb-fallback":
            ok = self.adb.forward_port()
            status_box = self.query_one("#agent-status-box", Static)
            if ok:
                self.query_one("#input-ip", Input).value = "127.0.0.1"
                status_box.update("[green]✔ 备用 ADB 映射已建立 (127.0.0.1:28888)[/green]")
            else:
                status_box.update("[red]✘ 未检测到 USB ADB 设备[/red]")

        elif btn_id == "btn-sync-wechat":
            log.write("[cyan][*] 请求手机端微信元数据 (纯无线通信)...[/cyan]")
            try:
                meta = await self.api.get_wechat_info()
                uin = meta.get("uin", "")
                device_id = meta.get("device_id", "")
                calc_key = compute_wechat_key(device_id, uin)
                log.write(f"[green][+] 获取微信凭据成功! UIN={uin}, Key={calc_key}[/green]")
                
                dest_enc = os.path.join(self.output_dir, "EnMicroMsg.db.enc")
                p_bar = self.query_one("#sync-progress", ProgressBar)
                
                def on_progress(downloaded, total, speed):
                    mb_speed = speed / (1024 * 1024)
                    if total > 0:
                        p_bar.update(total=total, progress=downloaded)
                        self.query_one("#lbl-progress", Label).update(
                            f"微信数据库传输中: {downloaded/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB (局域网速率: {mb_speed:.2f} MB/s)"
                        )

                log.write("[cyan][*] 手机端 SukiSU 管道正在直接回传 EnMicroMsg.db...[/cyan]")
                await self.api.download_file("/api/wechat/db", dest_enc, on_progress)
                log.write(f"[green][+] 数据库传输完成: {dest_enc}[/green]")

                # 自动解密
                dest_plain = os.path.join(self.output_dir, "EnMicroMsg_plain.db")
                log.write("[cyan][*] 启动 SQLCipher 解密转换...[/cyan]")
                ok = decrypt_wechat_db(dest_enc, dest_plain, calc_key)
                if ok:
                    log.write(f"[bold green][✔] 解密成功！标准明文数据库已就绪: {dest_plain}[/bold green]")
                    self.current_wechat_db = dest_plain
                    self._load_wechat_contacts()
                else:
                    log.write(f"[yellow][!] 自动解密未生成结果 (可能是环境缺少 sqlcipher)。可手动使用密码 '{calc_key}' 解密。[/yellow]")
                    self.current_wechat_db = dest_enc
                    self._load_wechat_contacts()
            except Exception as e:
                log.write(f"[red][✘] 同步微信数据出错: {str(e)}[/red]")

        elif btn_id == "btn-sync-qq":
            log.write("[cyan][*] 请求手机端 QQ 数据库元数据...[/cyan]")
            try:
                dest_qq = os.path.join(self.output_dir, "qq_data.db")
                p_bar = self.query_one("#sync-progress", ProgressBar)
                
                def on_qq_progress(downloaded, total, speed):
                    mb_speed = speed / (1024 * 1024)
                    if total > 0:
                        p_bar.update(total=total, progress=downloaded)
                        self.query_one("#lbl-progress", Label).update(
                            f"QQ数据库传输中: {downloaded/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB (局域网速率: {mb_speed:.2f} MB/s)"
                        )

                log.write("[cyan][*] 正在无线流式拉取 QQ 数据库...[/cyan]")
                await self.api.download_file("/api/qq/db", dest_qq, on_qq_progress)
                log.write(f"[bold green][✔] QQ 数据库传输完成: {dest_qq}[/bold green]")
                self.current_qq_db = dest_qq
            except Exception as e:
                log.write(f"[red][✘] 同步 QQ 出错: {str(e)}[/red]")

        elif btn_id == "btn-export-html":
            if not self.active_messages:
                log.write("[yellow]未选中任何有效会话消息可导出[/yellow]")
                return
            out_html = os.path.join(self.output_dir, f"{self.current_talker}_export.html")
            ChatExporter.export_to_html("微信聊天记录", self.current_talker_name, self.active_messages, out_html)
            log.write(f"[bold green][✔] 已成功导出 HTML 离线报告: file:///{out_html.replace(os.sep, '/')}[/bold green]")

        elif btn_id == "btn-export-csv":
            if not self.active_messages:
                log.write("[yellow]未选中任何有效会话消息可导出[/yellow]")
                return
            out_csv = os.path.join(self.output_dir, f"{self.current_talker}_export.csv")
            ChatExporter.export_to_csv(self.active_messages, out_csv)
            log.write(f"[bold green][✔] 已成功导出 CSV 数据表: file:///{out_csv.replace(os.sep, '/')}[/bold green]")

    def _load_wechat_contacts(self):
        """加载微信联系人到左侧列表"""
        if not self.current_wechat_db or not os.path.exists(self.current_wechat_db):
            return
        db = WeChatDatabase(self.current_wechat_db)
        contacts = db.get_contacts()
        c_list = self.query_one("#contacts-list", ListView)
        c_list.clear()
        for c in contacts:
            prefix = "[群] " if c["is_group"] else ""
            c_list.append(ListItem(Label(f"{prefix}{c['display_name']}"), name=c["username"]))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """用户点击联系人列表，加载对应聊天记录"""
        talker = event.item.name
        if not talker or not self.current_wechat_db:
            return
        self.current_talker = talker
        db = WeChatDatabase(self.current_wechat_db)
        messages = db.get_messages(talker, limit=100)
        self.active_messages = messages
        
        # 刷新右侧气泡展示
        title_label = self.query_one("#chat-title", Label)
        title_label.update(f"当前会话: {talker} (共 {len(messages)} 条已载入)")
        
        container = self.query_one("#chat-messages-container", VerticalScroll)
        container.remove_children()
        
        for m in messages:
            is_send = m["is_send"]
            cls_name = "msg-bubble-sent" if is_send else "msg-bubble-recv"
            sender_str = "我" if is_send else m["sender"]
            text = f"[bold]{sender_str}[/bold]:\n{m['content']}"
            container.mount(Static(text, classes=cls_name))

    def on_unmount(self):
        self.discovery.stop()

def main():
    app = ChatBackupApp()
    app.run()

if __name__ == "__main__":
    main()
