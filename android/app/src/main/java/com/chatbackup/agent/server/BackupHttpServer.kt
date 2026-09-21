package com.chatbackup.agent.server

import android.os.Build
import com.chatbackup.agent.extractor.QqExtractor
import com.chatbackup.agent.extractor.WeChatExtractor
import com.chatbackup.agent.su.SuExecutor
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.BufferedOutputStream
import java.io.BufferedReader
import java.io.InputStreamReader
import java.io.OutputStream
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.Executors

class BackupHttpServer(private val port: Int = 28888) {

    private var serverSocket: ServerSocket? = null
    private var isRunning = false
    private val threadPool = Executors.newCachedThreadPool()

    var logCallback: ((String) -> Unit)? = null

    fun start() {
        if (isRunning) return
        isRunning = true
        threadPool.execute {
            try {
                serverSocket = ServerSocket(port)
                logCallback?.invoke("服务已成功启动，监听端口: $port")
                while (isRunning) {
                    val client = serverSocket?.accept() ?: break
                    threadPool.execute { handleClient(client) }
                }
            } catch (e: Exception) {
                if (isRunning) {
                    logCallback?.invoke("服务异常终止: ${e.message}")
                }
            }
        }
    }

    fun stop() {
        isRunning = false
        try {
            serverSocket?.close()
        } catch (e: Exception) {
            // ignore
        }
        logCallback?.invoke("服务已停止")
    }

    private fun handleClient(socket: Socket) {
        try {
            val reader = BufferedReader(InputStreamReader(socket.getInputStream()))
            val firstLine = reader.readLine() ?: return
            val parts = firstLine.split(" ")
            if (parts.size < 2) return
            val method = parts[0]
            val path = parts[1]

            // 消费掉所有请求头
            var line: String?
            while (reader.readLine().also { line = it } != null) {
                if (line.isNullOrEmpty()) break
            }

            val out = BufferedOutputStream(socket.getOutputStream())
            when (path) {
                "/api/status" -> handleStatus(out)
                "/api/wechat/info" -> handleWeChatInfo(out)
                "/api/wechat/db" -> handleWeChatDb(out)
                "/api/qq/info" -> handleQqInfo(out)
                "/api/qq/db" -> handleQqDb(out)
                else -> sendResponse(out, 404, "application/json", "{\"error\":\"Not Found\"}")
            }
            out.flush()
        } catch (e: Exception) {
            logCallback?.invoke("处理请求出错: ${e.message}")
        } finally {
            try {
                socket.close()
            } catch (e: Exception) {
                // ignore
            }
        }
    }

    private fun handleStatus(out: OutputStream) {
        val rootOk = SuExecutor.checkRoot()
        val json = JSONObject().apply {
            put("status", "running")
            put("device_model", "${Build.MANUFACTURER} ${Build.MODEL}")
            put("android_version", Build.VERSION.RELEASE)
            put("has_root", rootOk)
            put("root_type", "SukiSU / KernelSU")
        }
        sendResponse(out, 200, "application/json", json.toString())
    }

    private fun handleWeChatInfo(out: OutputStream) {
        val info = WeChatExtractor.extractInfo()
        sendResponse(out, 200, "application/json", info.toString())
    }

    private fun handleQqInfo(out: OutputStream) {
        val info = QqExtractor.extractInfo()
        sendResponse(out, 200, "application/json", info.toString())
    }

    private fun handleWeChatDb(out: OutputStream) {
        val account = WeChatExtractor.findActiveAccount()
        if (account == null) {
            sendResponse(out, 404, "application/json", "{\"error\":\"WeChat database not found\"}")
            return
        }
        logCallback?.invoke("开始向电脑端流式传输微信数据库: ${account.dbPath} (${account.dbSize} 字节)")
        streamFileOverRoot(out, account.dbPath, account.dbSize)
    }

    private fun handleQqDb(out: OutputStream) {
        val account = QqExtractor.findActiveAccount()
        if (account == null) {
            sendResponse(out, 404, "application/json", "{\"error\":\"QQ database not found\"}")
            return
        }
        logCallback?.invoke("开始向电脑端流式传输QQ数据库: ${account.dbPath} (${account.dbSize} 字节)")
        streamFileOverRoot(out, account.dbPath, account.dbSize)
    }

    private fun streamFileOverRoot(out: OutputStream, filePath: String, fileSize: Long) {
        val header = "HTTP/1.1 200 OK\r\n" +
                "Content-Type: application/octet-stream\r\n" +
                "Content-Length: $fileSize\r\n" +
                "Connection: close\r\n\r\n"
        out.write(header.toByteArray())

        val pipe = SuExecutor.openPipeStream(filePath)
        if (pipe != null) {
            val (process, input) = pipe
            val buffer = ByteArray(65536)
            var bytesRead: Int
            val bufIn = BufferedInputStream(input)
            try {
                while (bufIn.read(buffer).also { bytesRead = it } != -1) {
                    out.write(buffer, 0, bytesRead)
                }
                out.flush()
                logCallback?.invoke("数据库传输完成！")
            } finally {
                try {
                    bufIn.close()
                    process.destroy()
                } catch (e: Exception) {
                    // ignore
                }
            }
        }
    }

    private fun sendResponse(out: OutputStream, code: Int, contentType: String, body: String) {
        val bytes = body.toByteArray(Charsets.UTF_8)
        val header = "HTTP/1.1 $code OK\r\n" +
                "Content-Type: $contentType; charset=utf-8\r\n" +
                "Content-Length: ${bytes.size}\r\n" +
                "Connection: close\r\n\r\n"
        out.write(header.toByteArray())
        out.write(bytes)
        out.flush()
    }
}
