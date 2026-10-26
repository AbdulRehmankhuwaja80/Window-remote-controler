package com.remodesk.client.data

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

class TokenManager(context: Context) {

    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val prefs: SharedPreferences = try {
        EncryptedSharedPreferences.create(
            context,
            "remodesk_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    } catch (e: Exception) {
        // Fallback to standard prefs if hardware keystore error on older emulators
        context.getSharedPreferences("remodesk_fallback_prefs", Context.MODE_PRIVATE)
    }

    var authToken: String?
        get() = prefs.getString(KEY_AUTH_TOKEN, null)
        set(value) = prefs.edit().putString(KEY_AUTH_TOKEN, value).apply()

    var refreshToken: String?
        get() = prefs.getString(KEY_REFRESH_TOKEN, null)
        set(value) = prefs.edit().putString(KEY_REFRESH_TOKEN, value).apply()

    var serverUrl: String
        get() = prefs.getString(KEY_SERVER_URL, "http://10.0.2.2:8000") ?: "http://10.0.2.2:8000"
        set(value) = prefs.edit().putString(KEY_SERVER_URL, value).apply()

    var userEmail: String?
        get() = prefs.getString(KEY_USER_EMAIL, null)
        set(value) = prefs.edit().putString(KEY_USER_EMAIL, value).apply()

    var touchpadSensitivity: Float
        get() = prefs.getFloat(KEY_TOUCHPAD_SENSITIVITY, 1.2f)
        set(value) = prefs.edit().putFloat(KEY_TOUCHPAD_SENSITIVITY, value).apply()

    var isBiometricEnabled: Boolean
        get() = prefs.getBoolean(KEY_BIOMETRIC, false)
        set(value) = prefs.edit().putBoolean(KEY_BIOMETRIC, value).apply()

    var streamingQuality: String
        get() = prefs.getString(KEY_STREAMING_QUALITY, "Balanced (1080p / 30fps)") ?: "Balanced (1080p / 30fps)"
        set(value) = prefs.edit().putString(KEY_STREAMING_QUALITY, value).apply()

    var maxReconnectAttempts: Int
        get() = prefs.getInt(KEY_MAX_RECONNECT_ATTEMPTS, 5)
        set(value) = prefs.edit().putInt(KEY_MAX_RECONNECT_ATTEMPTS, value).apply()

    var reconnectTimeoutSeconds: Int
        get() = prefs.getInt(KEY_RECONNECT_TIMEOUT_SEC, 30)
        set(value) = prefs.edit().putInt(KEY_RECONNECT_TIMEOUT_SEC, value).apply()

    var autoReconnect: Boolean
        get() = prefs.getBoolean(KEY_AUTO_RECONNECT, true)
        set(value) = prefs.edit().putBoolean(KEY_AUTO_RECONNECT, value).apply()

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val KEY_AUTH_TOKEN = "auth_token"
        private const val KEY_REFRESH_TOKEN = "refresh_token"
        private const val KEY_SERVER_URL = "server_url"
        private const val KEY_USER_EMAIL = "user_email"
        private const val KEY_TOUCHPAD_SENSITIVITY = "touchpad_sensitivity"
        private const val KEY_BIOMETRIC = "biometric_enabled"
        private const val KEY_STREAMING_QUALITY = "streaming_quality"
        private const val KEY_MAX_RECONNECT_ATTEMPTS = "max_reconnect_attempts"
        private const val KEY_RECONNECT_TIMEOUT_SEC = "reconnect_timeout_sec"
        private const val KEY_AUTO_RECONNECT = "auto_reconnect"
    }
}
