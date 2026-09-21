import csv
import datetime
import html
import os
from typing import List, Dict, Any

class ChatExporter:
    @staticmethod
    def _format_time(timestamp_ms: int) -> str:
        try:
            sec = timestamp_ms / 1000.0
            return datetime.datetime.fromtimestamp(sec).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(timestamp_ms)

    @classmethod
    def export_to_html(
        cls,
        title: str,
        talker_name: str,
        messages: List[Dict[str, Any]],
        output_path: str
    ) -> str:
        """导出为现代化高颜值的离线单文件 HTML"""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        
        # 预处理消息数据转为 JSON 嵌入
        msg_items = []
        for m in messages:
            time_str = cls._format_time(m.get("create_time", 0))
            is_send = m.get("is_send", False)
            content = html.escape(str(m.get("content", "")))
            sender = html.escape(str(m.get("sender", "Me" if is_send else talker_name)))
            msg_items.append(f"""
            <div class="message {'sent' if is_send else 'received'}">
                <div class="avatar">{'我' if is_send else sender[:1]}</div>
                <div class="bubble">
                    <div class="meta">{sender} · {time_str}</div>
                    <div class="text">{content}</div>
                </div>
            </div>
            """)

        html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title)} - {html.escape(talker_name)}</title>
    <style>
        :root {{
            --bg-color: #0d1117;
            --card-bg: #161b22;
            --border-color: #30363d;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --bubble-sent: #238636;
            --bubble-recv: #21262d;
            --accent: #58a6ff;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: var(--bg-color);
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
            display: flex;
            flex-direction: column;
            height: 100vh;
        }}
        header {{
            background: var(--card-bg);
            border-bottom: 1px solid var(--border-color);
            padding: 16px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        header h1 {{ font-size: 1.25rem; font-weight: 600; }}
        .search-box input {{
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 8px 14px;
            border-radius: 6px;
            outline: none;
            width: 260px;
        }}
        .search-box input:focus {{ border-color: var(--accent); }}
        main {{
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}
        .message {{
            display: flex;
            gap: 12px;
            max-width: 75%;
        }}
        .message.received {{ align-self: flex-start; }}
        .message.sent {{
            align-self: flex-end;
            flex-direction: row-reverse;
        }}
        .avatar {{
            width: 38px;
            height: 38px;
            border-radius: 50%;
            background: #30363d;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.9rem;
            flex-shrink: 0;
        }}
        .message.sent .avatar {{ background: #1f6feb; }}
        .bubble {{
            background: var(--bubble-recv);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 10px 14px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.15);
        }}
        .message.sent .bubble {{
            background: var(--bubble-sent);
            border-color: #2ea043;
        }}
        .meta {{
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }}
        .message.sent .meta {{ color: #e6edf3c2; }}
        .text {{
            font-size: 0.95rem;
            line-height: 1.5;
            white-space: pre-wrap;
            word-break: break-word;
        }}
    </style>
</head>
<body>
    <header>
        <div>
            <h1>{html.escape(talker_name)}</h1>
            <span style="font-size:0.8rem; color:var(--text-secondary);">共 {len(messages)} 条消息</span>
        </div>
        <div class="search-box">
            <input type="text" id="filterInput" placeholder="按内容或发言者搜索..." oninput="filterMessages()">
        </div>
    </header>
    <main id="chatContainer">
        {''.join(msg_items)}
    </main>
    <script>
        function filterMessages() {{
            const query = document.getElementById('filterInput').value.toLowerCase();
            const items = document.querySelectorAll('.message');
            items.forEach(el => {{
                const text = el.innerText.toLowerCase();
                el.style.display = text.includes(query) ? 'flex' : 'none';
            }});
        }}
    </script>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path

    @classmethod
    def export_to_csv(cls, messages: List[Dict[str, Any]], output_path: str) -> str:
        """导出为 CSV"""
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["时间", "发送者", "是否我发送", "内容", "消息ID"])
            for m in messages:
                writer.writerow([
                    cls._format_time(m.get("create_time", 0)),
                    m.get("sender", ""),
                    "是" if m.get("is_send") else "否",
                    m.get("content", ""),
                    m.get("msg_id", "")
                ])
        return output_path
