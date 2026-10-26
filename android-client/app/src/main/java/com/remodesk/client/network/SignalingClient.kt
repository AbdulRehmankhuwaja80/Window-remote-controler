package com.remodesk.client.network

import android.util.Log
import com.google.gson.Gson
import com.google.gson.JsonObject
import com.google.gson.JsonParser
import okhttp3.*
import java.util.concurrent.TimeUnit

class SignalingClient(
    private val wsUrl: String,
    private val token: String
) {
    private val TAG = "SignalingClient"
    private val gson = Gson()
    private var webSocket: WebSocket? = null
    private val client = OkHttpClient.Builder()
        .pingInterval(15, TimeUnit.SECONDS)
        .build()

    var onConnected: (() -> Unit)? = null
    var onDisconnected: (() -> Unit)? = null
    var onSessionAccepted: ((sessionId: String) -> Unit)? = null
    var onSessionRejected: ((reason: String) -> Unit)? = null
    var onOfferReceived: ((sdp: String) -> Unit)? = null
    var onAnswerReceived: ((sdp: String) -> Unit)? = null
    var onIceCandidateReceived: ((candidate: String) -> Unit)? = null
    var onSessionTerminated: ((reason: String) -> Unit)? = null
    var onDesktopFrameReceived: ((data: String) -> Unit)? = null
    var onDeviceStatusUpdate: ((deviceId: String, status: String) -> Unit)? = null
    var onFileListReceived: ((path: String, entries: List<com.remodesk.client.data.FileItem>?, error: String?) -> Unit)? = null
    var onFileReadChunkReceived: ((path: String, offset: Long, data: String?, isEof: Boolean, sha256: String?, error: String?) -> Unit)? = null
    var onFileWriteChunkResponse: ((path: String, offset: Long, success: Boolean, isComplete: Boolean, error: String?) -> Unit)? = null
    var onFileDeleteResponse: ((path: String, success: Boolean, error: String?) -> Unit)? = null
    var onClipboardReceived: ((text: String) -> Unit)? = null

    fun connect() {
        val fullUrl = "$wsUrl?role=client&token=$token"
        val request = Request.Builder().url(fullUrl).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                Log.d(TAG, "Signaling WebSocket connected")
                onConnected?.invoke()
            }

            override fun onMessage(ws: WebSocket, text: String) {
                try {
                    val jObj = JsonParser.parseString(text).asJsonObject
                    val type = jObj.get("type")?.asString ?: return

                    when (type) {
                        "registered" -> {
                            Log.d(TAG, "Client registered: ${jObj.get("client_id")?.asString}")
                        }
                        "session_response" -> {
                            val accepted = jObj.get("accepted")?.asBoolean ?: false
                            val sessionId = jObj.get("session_id")?.asString ?: ""
                            val reason = jObj.get("reason")?.asString ?: "Connection declined"
                            if (accepted) {
                                onSessionAccepted?.invoke(sessionId)
                            } else {
                                onSessionRejected?.invoke(reason)
                            }
                        }
                        "webrtc_offer" -> {
                            val sdp = jObj.get("sdp")?.asString ?: ""
                            onOfferReceived?.invoke(sdp)
                        }
                        "webrtc_answer" -> {
                            val sdp = jObj.get("sdp")?.asString ?: ""
                            onAnswerReceived?.invoke(sdp)
                        }
                        "ice_candidate" -> {
                            val candidate = jObj.get("candidate")?.asString ?: ""
                            onIceCandidateReceived?.invoke(candidate)
                        }
                        "session_terminated" -> {
                            val reason = jObj.get("reason")?.asString ?: "Session ended"
                            onSessionTerminated?.invoke(reason)
                        }
                        "desktop_frame" -> {
                            val data = jObj.get("data")?.asString ?: ""
                            onDesktopFrameReceived?.invoke(data)
                        }
                        "device_status_update" -> {
                            val devId = jObj.get("device_id")?.asString ?: ""
                            val status = jObj.get("status")?.asString ?: "OFFLINE"
                            onDeviceStatusUpdate?.invoke(devId, status)
                        }
                        "fs_list_response" -> {
                            val path = jObj.get("path")?.asString ?: ""
                            val err = jObj.get("error")?.asString
                            val entriesJson = jObj.get("entries")
                            val entries = if (entriesJson != null && entriesJson.isJsonArray) {
                                gson.fromJson(entriesJson, Array<com.remodesk.client.data.FileItem>::class.java).toList()
                            } else null
                            onFileListReceived?.invoke(path, entries, err)
                        }
                        "fs_read_chunk_response" -> {
                            val path = jObj.get("path")?.asString ?: ""
                            val offset = jObj.get("offset")?.asLong ?: 0L
                            val data = jObj.get("data")?.asString
                            val isEof = jObj.get("is_eof")?.asBoolean ?: false
                            val sha256 = jObj.get("sha256")?.asString
                            val err = jObj.get("error")?.asString
                            onFileReadChunkReceived?.invoke(path, offset, data, isEof, sha256, err)
                        }
                        "fs_write_chunk_response" -> {
                            val path = jObj.get("path")?.asString ?: ""
                            val offset = jObj.get("offset")?.asLong ?: 0L
                            val success = jObj.get("success")?.asBoolean ?: false
                            val isComplete = jObj.get("is_complete")?.asBoolean ?: false
                            val err = jObj.get("error")?.asString
                            onFileWriteChunkResponse?.invoke(path, offset, success, isComplete, err)
                        }
                        "fs_delete_response" -> {
                            val path = jObj.get("path")?.asString ?: ""
                            val success = jObj.get("success")?.asBoolean ?: false
                            val err = jObj.get("error")?.asString
                            onFileDeleteResponse?.invoke(path, success, err)
                        }
                        "clipboard_sync" -> {
                            val textContent = jObj.get("text")?.asString ?: ""
                            onClipboardReceived?.invoke(textContent)
                        }
                    }
                } catch (e: Exception) {
                    Log.e(TAG, "Error parsing signaling message: ${e.message}")
                }
            }

            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                Log.e(TAG, "Signaling failure: ${t.message}")
                onDisconnected?.invoke()
            }

            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                Log.d(TAG, "Signaling closed: $reason")
                onDisconnected?.invoke()
            }
        })
    }

    fun requestSession(
        deviceId: String,
        sessionId: String,
        clientInfo: String = "Android Mobile",
        width: Int = 1920,
        height: Int = 1080,
        quality: String = "Balanced (1080p / 30fps)"
    ) {
        val msg = JsonObject().apply {
            addProperty("type", "session_request")
            addProperty("target_device_id", deviceId)
            addProperty("session_id", sessionId)
            addProperty("client_info", clientInfo)
            addProperty("width", width)
            addProperty("height", height)
            addProperty("quality", quality)
        }
        send(msg.toString())
    }

    fun sendOffer(sessionId: String, sdp: String) {
        val msg = JsonObject().apply {
            addProperty("type", "webrtc_offer")
            addProperty("session_id", sessionId)
            addProperty("sdp", sdp)
        }
        send(msg.toString())
    }

    fun sendAnswer(sessionId: String, sdp: String) {
        val msg = JsonObject().apply {
            addProperty("type", "webrtc_answer")
            addProperty("session_id", sessionId)
            addProperty("sdp", sdp)
        }
        send(msg.toString())
    }

    fun sendIceCandidate(sessionId: String, candidate: String) {
        val msg = JsonObject().apply {
            addProperty("type", "ice_candidate")
            addProperty("session_id", sessionId)
            addProperty("candidate", candidate)
        }
        send(msg.toString())
    }

    fun endSession(sessionId: String, reason: String = "User disconnected") {
        val msg = JsonObject().apply {
            addProperty("type", "session_end")
            addProperty("session_id", sessionId)
            addProperty("reason", reason)
        }
        send(msg.toString())
    }

    fun requestFileList(deviceId: String, path: String) {
        val msg = JsonObject().apply {
            addProperty("type", "fs_list")
            addProperty("target_device_id", deviceId)
            addProperty("device_id", deviceId)
            addProperty("path", path)
        }
        send(msg.toString())
    }

    fun requestReadFileChunk(deviceId: String, path: String, offset: Long, length: Int = 65536) {
        val msg = JsonObject().apply {
            addProperty("type", "fs_read_chunk")
            addProperty("target_device_id", deviceId)
            addProperty("device_id", deviceId)
            addProperty("path", path)
            addProperty("offset", offset)
            addProperty("length", length)
        }
        send(msg.toString())
    }

    fun requestWriteFileChunk(deviceId: String, path: String, offset: Long, base64Data: String, isComplete: Boolean, overwrite: Boolean) {
        val msg = JsonObject().apply {
            addProperty("type", "fs_write_chunk")
            addProperty("target_device_id", deviceId)
            addProperty("device_id", deviceId)
            addProperty("path", path)
            addProperty("offset", offset)
            addProperty("data", base64Data)
            addProperty("is_complete", isComplete)
            addProperty("overwrite", overwrite)
        }
        send(msg.toString())
    }

    fun requestDeleteFile(deviceId: String, path: String) {
        val msg = JsonObject().apply {
            addProperty("type", "fs_delete")
            addProperty("target_device_id", deviceId)
            addProperty("device_id", deviceId)
            addProperty("path", path)
        }
        send(msg.toString())
    }

    fun sendClipboard(text: String) {
        val msg = JsonObject().apply {
            addProperty("type", "clipboard_sync")
            addProperty("text", text)
        }
        send(msg.toString())
    }

    fun sendQuality(sessionId: String, quality: String) {
        val msg = JsonObject().apply {
            addProperty("type", "set_quality")
            addProperty("session_id", sessionId)
            addProperty("quality", quality)
        }
        send(msg.toString())
    }

    fun selectMonitor(sessionId: String, monitorIndex: Int) {
        val msg = JsonObject().apply {
            addProperty("type", "select_monitor")
            addProperty("session_id", sessionId)
            addProperty("monitor_index", monitorIndex)
        }
        send(msg.toString())
    }

    fun sendRaw(json: String) {
        send(json)
    }

    private fun send(json: String) {
        webSocket?.send(json)
    }

    fun disconnect() {
        webSocket?.close(1000, "Normal closure")
        webSocket = null
    }
}
