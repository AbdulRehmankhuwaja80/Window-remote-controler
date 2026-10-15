package com.remodesk.client.webrtc

import com.google.gson.JsonObject

object InputEventProtocol {

    fun serializeMouseMove(normX: Float, normY: Float): String {
        return JsonObject().apply {
            addProperty("type", "mouse_move")
            addProperty("x", normX)
            addProperty("y", normY)
        }.toString()
    }

    fun serializeMouseDelta(dx: Int, dy: Int): String {
        return JsonObject().apply {
            addProperty("type", "mouse_delta")
            addProperty("dx", dx)
            addProperty("dy", dy)
        }.toString()
    }

    fun serializeMouseButton(button: String, action: String): String {
        return JsonObject().apply {
            addProperty("type", "mouse_button")
            addProperty("button", button) // "left", "right", "middle"
            addProperty("action", action) // "click", "down", "up", "double_click"
        }.toString()
    }

    fun serializeMouseScroll(dx: Int, dy: Int): String {
        return JsonObject().apply {
            addProperty("type", "mouse_scroll")
            addProperty("dx", dx)
            addProperty("dy", dy)
        }.toString()
    }

    fun serializeKeyEvent(vk: Int, action: String, extended: Boolean = false): String {
        return JsonObject().apply {
            addProperty("type", "key_event")
            addProperty("vk", vk)
            addProperty("action", action) // "down", "up"
            addProperty("extended", extended)
        }.toString()
    }

    fun serializeTextInput(text: String): String {
        return JsonObject().apply {
            addProperty("type", "text_input")
            addProperty("text", text)
        }.toString()
    }

    fun serializeClipboardSync(content: String): String {
        return JsonObject().apply {
            addProperty("type", "clipboard_sync")
            addProperty("content", content)
        }.toString()
    }

    fun serializePing(timestamp: Long = System.currentTimeMillis()): String {
        return JsonObject().apply {
            addProperty("type", "ping")
            addProperty("timestamp", timestamp)
        }.toString()
    }
}
