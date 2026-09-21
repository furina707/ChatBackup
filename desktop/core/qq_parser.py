import sqlite3
import os
from typing import List, Dict, Any

class QqDatabase:
    """QQ 数据库解析引擎（支持传统版本与新版 NT 架构）"""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.is_nt = self._detect_nt()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _detect_nt(self) -> bool:
        """检测是否为 NT 架构数据库"""
        if not os.path.exists(self.db_path):
            return False
        try:
            with self._get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'nt_%' OR name LIKE 'msg_record%'")
                return cursor.fetchone() is not None
        except Exception:
            return False

    def get_contacts(self) -> List[Dict[str, Any]]:
        """获取 QQ 好友与群聊列表"""
        contacts = []
        if not os.path.exists(self.db_path):
            return contacts

        with self._get_conn() as conn:
            cursor = conn.cursor()
            if self.is_nt:
                # NT 架构表解析
                try:
                    cursor.execute("""
                    SELECT peer_uid as id, peer_name as name, chat_type
                    FROM contact_table
                    UNION
                    SELECT group_code as id, group_name as name, 2 as chat_type
                    FROM group_table
                    """)
                    for row in cursor.fetchall():
                        is_group = row["chat_type"] == 2
                        contacts.append({
                            "id": str(row["id"]),
                            "display_name": row["name"] or str(row["id"]),
                            "is_group": is_group
                        })
                except Exception:
                    pass
            else:
                # 传统 QQ 数据库结构
                try:
                    # 获取好友
                    cursor.execute("SELECT uin, name, remark FROM Friends")
                    for row in cursor.fetchall():
                        uin = str(row["uin"])
                        remark = row["remark"]
                        name = row["name"]
                        display = remark if remark else (name if name else uin)
                        contacts.append({
                            "id": uin,
                            "display_name": display,
                            "is_group": False
                        })
                except Exception:
                    pass

                try:
                    # 获取群聊
                    cursor.execute("SELECT troopuin, troopname FROM TroopInfo")
                    for row in cursor.fetchall():
                        troop_uin = str(row["troopuin"])
                        t_name = row["troopname"] or troop_uin
                        contacts.append({
                            "id": troop_uin,
                            "display_name": t_name,
                            "is_group": True
                        })
                except Exception:
                    pass

        return contacts

    def get_messages(self, target_id: str, is_group: bool, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        """获取指定联系人或群的历史消息"""
        messages = []
        if not os.path.exists(self.db_path):
            return messages

        with self._get_conn() as conn:
            cursor = conn.cursor()
            if self.is_nt:
                # NT 消息查询
                try:
                    query = """
                    SELECT msg_id, sender_uid, msg_time, msg_content, is_send
                    FROM msg_table
                    WHERE peer_uid = ?
                    ORDER BY msg_time ASC
                    LIMIT ? OFFSET ?
                    """
                    cursor.execute(query, (target_id, limit, offset))
                    for row in cursor.fetchall():
                        messages.append({
                            "msg_id": row["msg_id"],
                            "sender": str(row["sender_uid"]),
                            "create_time": row["msg_time"] * 1000,
                            "content": row["msg_content"] or "",
                            "is_send": bool(row["is_send"])
                        })
                except Exception:
                    pass
            else:
                # 传统架构：表名通常是 mr_friend_<MD5(uin)> 或 mr_troop_<MD5(uin)>
                import hashlib
                table_prefix = "mr_troop_" if is_group else "mr_friend_"
                table_name = table_prefix + hashlib.md5(target_id.encode("utf-8")).hexdigest().upper()
                try:
                    query = f"""
                    SELECT time, senderuin, msgData, issend
                    FROM {table_name}
                    ORDER BY time ASC
                    LIMIT ? OFFSET ?
                    """
                    cursor.execute(query, (limit, offset))
                    for row in cursor.fetchall():
                        # msgData 可能是 utf-8 或 GBK 字符串，或序列化字段
                        raw_data = row["msgData"]
                        text = ""
                        if isinstance(raw_data, bytes):
                            try:
                                text = raw_data.decode("utf-8")
                            except Exception:
                                try:
                                    text = raw_data.decode("gbk", errors="ignore")
                                except Exception:
                                    text = "[非文本数据]"
                        else:
                            text = str(raw_data or "")

                        messages.append({
                            "msg_id": f"{row['time']}_{row['senderuin']}",
                            "sender": str(row["senderuin"]),
                            "create_time": row["time"] * 1000,
                            "content": text,
                            "is_send": row["issend"] == 1
                        })
                except Exception:
                    pass

        return messages
