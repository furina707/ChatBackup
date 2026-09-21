package com.chatbackup.agent.extractor

import com.chatbackup.agent.su.SuExecutor
import org.json.JSONObject

object QqExtractor {

    private const val QQ_PACKAGE = "com.tencent.mobileqq"
    private const val BASE_PATH = "/data/data/$QQ_PACKAGE"

    data class QqAccount(
        val accountId: String,
        val dbPath: String,
        val dbSize: Long,
        val isNt: Boolean
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
            result.put("error", "Mobile QQ data not found")
            return result
        }

        result.put("success", true)
        result.put("account_id", account.accountId)
        result.put("db_path", account.dbPath)
        result.put("db_size", account.dbSize)
        result.put("is_nt", account.isNt)
        return result
    }

    fun findActiveAccount(): QqAccount? {
        val dbDir = "$BASE_PATH/databases"

        // 优先检查新版 NT 架构数据库
        val ntDbPath = "$dbDir/nt_msg.db"
        val ntSize = SuExecutor.getFileSize(ntDbPath)
        if (ntSize > 0) {
            return QqAccount(
                accountId = "NT_QQ",
                dbPath = ntDbPath,
                dbSize = ntSize,
                isNt = true
            )
        }

        // 检查老版 <QQ号>.db
        val filesOutput = SuExecutor.exec("ls $dbDir/[0-9]*.db 2>/dev/null")
        val dbs = filesOutput.lines().map { it.trim() }.filter { it.isNotEmpty() }
        for (dbPath in dbs) {
            val size = SuExecutor.getFileSize(dbPath)
            if (size > 0) {
                val uin = dbPath.substringAfterLast("/").substringBefore(".db")
                return QqAccount(
                    accountId = uin,
                    dbPath = dbPath,
                    dbSize = size,
                    isNt = false
                )
            }
        }
        return null
    }
}
