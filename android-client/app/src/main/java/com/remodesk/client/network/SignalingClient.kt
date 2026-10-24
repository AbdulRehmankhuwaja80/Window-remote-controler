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
