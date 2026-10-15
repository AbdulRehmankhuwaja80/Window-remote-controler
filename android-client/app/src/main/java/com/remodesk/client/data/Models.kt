package com.remodesk.client.data

import com.google.gson.annotations.SerializedName

data class User(
    val id: String,
    val email: String,
    @SerializedName("full_name") val fullName: String?,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("created_at") val createdAt: String
)

data class TokenResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
    val user: User
)

data class Device(
    val id: String,
    @SerializedName("device_name") val deviceName: String,
    val hostname: String?,
    @SerializedName("os_info") val osInfo: String,
    val status: String, // ONLINE, OFFLINE, IN_SESSION, PAUSED
    @SerializedName("is_remote_enabled") val isRemoteEnabled: Boolean,
    @SerializedName("ip_address") val ipAddress: String?,
    @SerializedName("last_seen") val lastSeen: String
)

data class IceServer(
    val urls: List<String>,
    val username: String? = null,
    val credential: String? = null
)

data class WebRtcConfig(
    @SerializedName("ice_servers") val iceServers: List<IceServer>
)

data class SessionStartResponse(
    @SerializedName("session_id") val sessionId: String,
    @SerializedName("device_id") val deviceId: String,
    val status: String,
    @SerializedName("ice_servers") val iceServers: List<IceServer>
)

data class FileItem(
    val name: String,
    val path: String,
    @SerializedName("is_directory") val isDirectory: Boolean,
    val size: Long,
    @SerializedName("modified_at") val modifiedAt: String
)

sealed class InputEvent {
    data class MouseMove(val x: Float, val y: Float) : InputEvent()
    data class MouseDelta(val dx: Int, val dy: Int) : InputEvent()
    data class MouseButton(val button: String, val action: String) : InputEvent() // "left", "right"; "down", "up", "click", "double_click"
    data class MouseScroll(val dx: Int, val dy: Int) : InputEvent()
    data class KeyEvent(val vk: Int, val action: String, val extended: Boolean = false) : InputEvent()
    data class TextInput(val text: String) : InputEvent()
    data class ClipboardSync(val content: String) : InputEvent()
    data class Ping(val timestamp: Long) : InputEvent()
}
