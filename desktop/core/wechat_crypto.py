import hashlib
import sqlite3
import subprocess
import shutil
import os
from typing import List, Dict, Any, Optional

def compute_wechat_key(device_id: str, uin: str) -> str:
    """
    计算微信数据库 SQLCipher 密码
    Password = MD5(DeviceID + UIN)[0:7] (小写)
    """
    raw = (str(device_id).strip() + str(uin).strip()).encode("utf-8")
    return hashlib.md5(raw).hexdigest()[:7].lower()

class WeChatDatabase:
    """微信已解密数据库查询引擎"""
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_contacts(self) -> List[Dict[str, Any]]:
        """获取联系人与群聊列表"""
        contacts = []
        if not os.path.exists(self.db_path):
            return contacts
            
        with self._get_conn() as conn:
            cursor = conn.cursor()
            try:
                # rcontact 表存储了好友和群聊
                query = """
                SELECT username, alias, conRemark, nickname, type, verifyFlag
                FROM rcontact
                WHERE username NOT LIKE '%@app' 
                  AND username NOT LIKE 'gh_%'
                  AND username NOT IN ('fmessage', 'medianote', 'qmessage', 'qqsync')
                ORDER BY 
                    CASE WHEN conRemark IS NOT NULL AND conRemark != '' THEN 0 ELSE 1 END,
                    nickname ASC
                """
                cursor.execute(query)
                for row in cursor.fetchall():
                    uname = row["username"]
                    is_group = uname.endswith("@chatroom")
                    remark = row["conRemark"]
                    nick = row["nickname"]
                    alias = row["alias"]
                    
                    display_name = remark if remark else (nick if nick else (alias if alias else uname))
                    contacts.append({
                        "username": uname,
                        "display_name": display_name,
                        "nickname": nick or "",
                        "remark": remark or "",
                        "is_group": is_group
                    })
            except Exception as e:
                print(f"Error querying contacts: {e}")
        return contacts

    def get_messages(self, talker: str, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        """获取指定会话的历史消息"""
        messages = []
        if not os.path.exists(self.db_path):
            return messages

        with self._get_conn() as conn:
            cursor = conn.cursor()
            try:
                query = """
                SELECT msgId, msgSvrId, type, status, isSend, createTime, talker, content
                FROM message
                WHERE talker = ?
                ORDER BY createTime ASC
                LIMIT ? OFFSET ?
                """
                cursor.execute(query, (talker, limit, offset))
                for row in cursor.fetchall():
                    content = row["content"] or ""
                    # 群聊中如果是别人发的消息，开头格式通常是: wxid_xxx:\n消息内容
                    sender = talker
                    is_send = row["isSend"] == 1
                    
                    if talker.endswith("@chatroom") and not is_send and ":\n" in content:
                        parts = content.split(":\n", 1)
                        sender = parts[0]
                        content = parts[1]

                    messages.append({
                        "msg_id": row["msgId"],
                        "msg_svr_id": row["msgSvrId"],
                        "type": row["type"],
                        "is_send": is_send,
                        "create_time": row["createTime"],
                        "sender": sender,
                        "content": content
                    })
            except Exception as e:
                print(f"Error querying messages: {e}")
        return messages

    def get_message_count(self, talker: str) -> int:
        """获取指定会话的消息总数"""
        if not os.path.exists(self.db_path):
            return 0
        with self._get_conn() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM message WHERE talker = ?", (talker,))
                res = cursor.fetchone()
                return res[0] if res else 0
            except Exception:
                return 0

def decrypt_wechat_db(
    encrypted_db_path: str,
    output_plain_db: str,
    key: str,
    sqlcipher_path: Optional[str] = None
) -> bool:
    """
    使用 SQLCipher 导出明文数据库
    """
    sqlcipher_bin = sqlcipher_path or shutil.which("sqlcipher")
    if not sqlcipher_bin:
        # 若未找到系统命令，检测本地预置路径
        local_candidate = os.path.join(os.path.dirname(__file__), "..", "bin", "sqlcipher.exe")
        if os.path.exists(local_candidate):
            sqlcipher_bin = local_candidate

    if not sqlcipher_bin:
        # 若实在没有 sqlcipher 命令行，检查是否能以原生 sqlite3 打开（若已是明文）
        try:
            conn = sqlite3.connect(encrypted_db_path)
            conn.execute("SELECT count(*) FROM sqlite_master")
            conn.close()
            shutil.copyfile(encrypted_db_path, output_plain_db)
            return True
        except Exception:
            return False

    # 构造 SQLCipher 导出命令脚本
    # 微信 Android 常用配置：cipher_page_size=1024, kdf_iter=64000, cipher_use_hmac=OFF/ON
    configs = [
        # 配置 1: 早期及常见兼容模式 (HMAC OFF, page_size 1024)
        f"PRAGMA key = '{key}';\nPRAGMA cipher_use_hmac = OFF;\nPRAGMA cipher_page_size = 1024;\n",
        # 配置 2: 4.x/现代模式 (HMAC ON, page_size 1024)
        f"PRAGMA key = '{key}';\nPRAGMA cipher_page_size = 1024;\nPRAGMA kdf_iter = 64000;\n",
        # 配置 3: 现代 4096 模式
        f"PRAGMA key = '{key}';\nPRAGMA cipher_page_size = 4096;\n"
    ]

    for cfg in configs:
        if os.path.exists(output_plain_db):
            try:
                os.remove(output_plain_db)
            except Exception:
                pass

        sql_script = f"""
{cfg}
ATTACH DATABASE '{output_plain_db}' AS plaintext KEY '';
SELECT sqlcipher_export('plaintext');
DETACH DATABASE plaintext;
.exit
"""
        try:
            proc = subprocess.run(
                [sqlcipher_bin, encrypted_db_path],
                input=sql_script,
                text=True,
                capture_output=True,
                timeout=30
            )
            # 检验生成的输出库是否包含标准表
            if os.path.exists(output_plain_db) and os.path.getsize(output_plain_db) > 0:
                try:
                    test_conn = sqlite3.connect(output_plain_db)
                    cursor = test_conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message'")
                    if cursor.fetchone():
                        test_conn.close()
                        return True
                    test_conn.close()
                except Exception:
                    pass
        except Exception:
            continue

    return False
