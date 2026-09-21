package com.chatbackup.agent.su

import java.io.BufferedReader
import java.io.InputStream
import java.io.InputStreamReader

object SuExecutor {

    /**
     * 检查设备是否具备并已授予 Root 权限 (SukiSU / KernelSU / Magisk)
     */
    fun checkRoot(): Boolean {
        return try {
            val process = Runtime.getRuntime().exec("su")
            val os = process.outputStream
            os.write("id\nexit\n".toByteArray())
            os.flush()
            val reader = BufferedReader(InputStreamReader(process.inputStream))
            val line = reader.readLine() ?: ""
            process.waitFor()
            line.contains("uid=0")
        } catch (e: Exception) {
            false
        }
    }

    /**
     * 执行 root 命令并返回文本输出
     */
    fun exec(command: String): String {
        return try {
            val process = Runtime.getRuntime().exec("su")
            val os = process.outputStream
            os.write("$command\nexit\n".toByteArray())
            os.flush()

            val reader = BufferedReader(InputStreamReader(process.inputStream))
            val sb = StringBuilder()
            var line: String?
            while (reader.readLine().also { line = it } != null) {
                sb.append(line).append("\n")
            }
            process.waitFor()
            sb.toString().trim()
        } catch (e: Exception) {
            ""
        }
    }

    /**
     * 以流的方式读取私有文件（零中间副本，直接通过管道读取）
     * 调用者需要负责关闭返回的 Process 或 InputStream
     */
    fun openPipeStream(filePath: String): Pair<Process, InputStream>? {
        return try {
            // 使用 su -c cat 流式读取
            val process = ProcessBuilder("su", "-c", "cat \"$filePath\"")
                .redirectErrorStream(false)
                .start()
            Pair(process, process.inputStream)
        } catch (e: Exception) {
            null
        }
    }

    /**
     * 获取目标文件大小（字节数）
     */
    fun getFileSize(filePath: String): Long {
        val out = exec("stat -c %s \"$filePath\" 2>/dev/null || wc -c < \"$filePath\" 2>/dev/null")
        return out.lines().firstOrNull()?.trim()?.toLongOrNull() ?: 0L
    }
}
