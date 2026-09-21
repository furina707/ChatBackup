package com.chatbackup.agent

import android.graphics.Color
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.chatbackup.agent.server.BackupHttpServer
import com.chatbackup.agent.server.DiscoveryBroadcaster
import com.chatbackup.agent.su.SuExecutor
import java.net.NetworkInterface
import java.util.Collections

class MainActivity : AppCompatActivity() {

    private var httpServer: BackupHttpServer? = null
    private var broadcaster: DiscoveryBroadcaster? = null
    private var isServing = false

    private lateinit var tvRootStatus: TextView
    private lateinit var tvIpAddress: TextView
    private lateinit var tvLogs: TextView
    private lateinit var btnToggle: Button

    private var currentIp: String = "127.0.0.1"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        tvRootStatus = findViewById(R.id.tv_root_status)
        tvIpAddress = findViewById(R.id.tv_ip_address)
        tvLogs = findViewById(R.id.tv_logs)
        btnToggle = findViewById(R.id.btn_toggle_server)

        checkRootStatus()
        currentIp = getLocalIpAddress()
        tvIpAddress.text = "本机局域网 IP: $currentIp:28888"

        httpServer = BackupHttpServer(28888).apply {
            logCallback = { msg ->
                runOnUiThread {
                    appendLog(msg)
                }
            }
        }

        btnToggle.setOnClickListener {
            if (isServing) {
                httpServer?.stop()
                broadcaster?.stop()
                isServing = false
                btnToggle.text = "启动无线备份服务 (免数据线)"
                btnToggle.setBackgroundColor(Color.parseColor("#1F6FEB"))
                appendLog("服务已停止")
            } else {
                httpServer?.start()
                broadcaster = DiscoveryBroadcaster(currentIp, 28888).apply {
                    start()
                }
                isServing = true
                btnToggle.text = "停止备份传输服务"
                btnToggle.setBackgroundColor(Color.parseColor("#DA3633"))
                appendLog("✔ 无线服务与局域网自动广播已启动")
            }
        }
    }

    private fun checkRootStatus() {
        Thread {
            val hasRoot = SuExecutor.checkRoot()
            runOnUiThread {
                if (hasRoot) {
                    tvRootStatus.text = "Root 状态: 已授权 (SukiSU / KernelSU)"
                    tvRootStatus.setTextColor(Color.parseColor("#3FB950"))
                    appendLog("✔ 成功获取内核级 Root 权限，可免 ADB 直接读取")
                } else {
                    tvRootStatus.text = "Root 状态: 未授权"
                    tvRootStatus.setTextColor(Color.parseColor("#F85149"))
                    appendLog("✘ 请在 SukiSU 管理器中授予本 App Root 权限")
                }
            }
        }.start()
    }

    private fun getLocalIpAddress(): String {
        try {
            val interfaces = Collections.list(NetworkInterface.getNetworkInterfaces())
            for (intf in interfaces) {
                val addrs = Collections.list(intf.inetAddresses)
                for (addr in addrs) {
                    if (!addr.isLoopbackAddress && !addr.isLinkLocalAddress) {
                        val host = addr.hostAddress ?: ""
                        if (!host.contains(":")) {
                            return host
                        }
                    }
                }
            }
        } catch (e: Exception) {
            // ignore
        }
        return "127.0.0.1"
    }

    private fun appendLog(msg: String) {
        val current = tvLogs.text.toString()
        tvLogs.text = "$current\n$msg"
    }

    override fun onDestroy() {
        super.onDestroy()
        httpServer?.stop()
        broadcaster?.stop()
    }
}
