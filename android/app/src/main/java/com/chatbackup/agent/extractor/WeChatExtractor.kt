package com.chatbackup.agent.extractor

import com.chatbackup.agent.su.SuExecutor
import org.json.JSONObject
import java.util.regex.Pattern

object WeChatExtractor {

    private const val MM_PACKAGE = "com.tencent.mm"
    private const val BASE_PATH = "/data/data/$MM_PACKAGE"

    data class WeChatAccount(
        val userHash: String,
        val uin: String,
        val deviceId: String,
        val dbPath: String,
        val dbSize: Long
    )

    fun extractInfo(): JSONObject {
        val result = JSONObject()
        if (!SuExecutor.checkRoot()) {
            result.put("success", false)
            result.put("error", "No root permission")
            return result
        }

        val account = findActiveAccount()
        if (account == null) {
            result.put("success", false)
            result.put("error", "WeChat data or active account not found")
            return result
        }

        result.put("success", true)
        result.put("user_hash", account.userHash)
        result.put("uin", account.uin)
        result.put("device_id", account.deviceId)
        result.put("db_path", account.dbPath)
        result.put("db_size", account.dbSize)
        return result
    }

    fun findActiveAccount(): WeChatAccount? {
        val microMsgPath = "$BASE_PATH/MicroMsg"
        // 查找 32 位的用户 md5 目录
        val dirOutput = SuExecutor.exec("ls -d $microMsgPath/[0-9a-fA-F]* 2>/dev/null")
        val dirs = dirOutput.lines().map { it.trim() }.filter { it.isNotEmpty() }

        // 获取 UIN
        val xmlContent = SuExecutor.exec("cat $BASE_PATH/shared_prefs/system_config_prefs.xml 2>/dev/null")
        var uin = ""
        val uinPattern = Pattern.compile("name=\"default_uin\" value=\"(-?\\d+)\"")
        val matcher = uinPattern.matcher(xmlContent)
        if (matcher.find()) {
            uin = matcher.group(1) ?: ""
        }

        // 获取 DeviceId (在 CompatibleInfo.cfg 中或从系统提取)
        var deviceId = ""
        val cfgPath = "$microMsgPath/CompatibleInfo.cfg"
        val cfgHex = SuExecutor.exec("xxd -p $cfgPath 2>/dev/null || hexdump -ve '1/1 \"%.2x\"' $cfgPath 2>/dev/null")
        if (cfgHex.isNotEmpty()) {
            // CompatibleInfo.cfg 中通常包含 16 字节或固定字符串 device id
            deviceId = cfgHex.take(32)
        }
        if (deviceId.isEmpty()) {
            // 降级方案：从系统设置中读取 android_id
            deviceId = SuExecutor.exec("settings get secure android_id 2>/dev/null").trim()
        }

        for (d in dirs) {
            val dbPath = "$d/EnMicroMsg.db"
            val size = SuExecutor.getFileSize(dbPath)
            if (size > 0) {
                val hash = d.substringAfterLast("/")
                return WeChatAccount(
                    userHash = hash,
                    uin = uin,
                    deviceId = deviceId,
                    dbPath = dbPath,
                    dbSize = size
                )
            }
        }
        return null
    }
}
