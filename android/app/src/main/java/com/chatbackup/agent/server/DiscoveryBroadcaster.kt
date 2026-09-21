package com.chatbackup.agent.server

import android.os.Build
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.util.concurrent.Executors

class DiscoveryBroadcaster(
    private val localIp: String,
    private val httpPort: Int = 28888,
    private val broadcastPort: Int = 28889
) {

    private var isBroadcasting = false
    private val executor = Executors.newSingleThreadExecutor()

    fun start() {
        if (isBroadcasting) return
        isBroadcasting = true

        executor.execute {
            var socket: DatagramSocket? = null
            try {
                socket = DatagramSocket()
                socket.broadcast = true

                val payload = JSONObject().apply {
                    put("device_model", "${Build.MANUFACTURER} ${Build.MODEL}")
                    put("ip", localIp)
                    put("port", httpPort)
                }.toString()

                val msg = "CHAT_BACKUP_AGENT:$payload".toByteArray(Charsets.UTF_8)
                val broadcastAddress = InetAddress.getByName("255.255.255.255")

                while (isBroadcasting) {
                    val packet = DatagramPacket(msg, msg.size, broadcastAddress, broadcastPort)
                    socket.send(packet)
                    Thread.sleep(2000)
                }
            } catch (e: Exception) {
                // ignore
            } finally {
                socket?.close()
            }
        }
    }

    fun stop() {
        isBroadcasting = false
    }
}
