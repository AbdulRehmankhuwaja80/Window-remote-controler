package com.remodesk.client

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.*
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.remodesk.client.data.Device
import com.remodesk.client.data.TokenManager
import com.remodesk.client.network.ApiService
import com.remodesk.client.network.SignalingClient
import com.remodesk.client.ui.screens.*
import com.remodesk.client.ui.theme.RemoDeskTheme
import com.remodesk.client.webrtc.WebRtcClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import org.webrtc.EglBase

class MainActivity : ComponentActivity() {

    private lateinit var tokenManager: TokenManager
    private val eglBase: EglBase by lazy { EglBase.create() }
    private var webRtcClient: WebRtcClient? = null
    private var signalingClient: SignalingClient? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        tokenManager = TokenManager(this)

        setContent {
            RemoDeskTheme {
                val navController = rememberNavController()
                val startDestination = if (tokenManager.authToken != null) "dashboard" else "login"

                NavHost(navController = navController, startDestination = startDestination) {
                    composable("login") {
                        LoginScreen(
                            tokenManager = tokenManager,
                            onLoginSuccess = {
                                navController.navigate("dashboard") {
                                    popUpTo("login") { inclusive = true }
                                }
                            },
                            onNavigateToRegister = {
                                navController.navigate("register")
                            }
                        )
                    }

                    composable("register") {
                        RegisterScreen(
                            tokenManager = tokenManager,
                            onRegisterSuccess = {
                                navController.navigate("dashboard") {
                                    popUpTo("register") { inclusive = true }
                                }
                            },
                            onNavigateBack = {
                                navController.popBackStack()
                            }
                        )
                    }

                    composable("dashboard") {
                        DashboardScreen(
                            tokenManager = tokenManager,
                            onConnectDevice = { device ->
                                initiateRemoteSession(device) {
                                    navController.navigate("remote/${device.id}/${device.deviceName}")
                                }
                            },
                            onNavigateToFileManager = { device ->
                                navController.navigate("files/${device.id}/${device.deviceName}")
                            },
                            onNavigateToSettings = {
                                navController.navigate("settings")
                            },
                            onLogout = {
                                tokenManager.authToken = null
                                navController.navigate("login") {
                                    popUpTo("dashboard") { inclusive = true }
                                }
                            }
                        )
                    }

                    composable(
                        "remote/{deviceId}/{deviceName}",
                        arguments = listOf(
                            navArgument("deviceId") { type = NavType.StringType },
                            navArgument("deviceName") { type = NavType.StringType }
                        )
                    ) { backStackEntry ->
                        val devId = backStackEntry.arguments?.getString("deviceId") ?: ""
                        val devName = backStackEntry.arguments?.getString("deviceName") ?: "Windows PC"

                        val rtc = webRtcClient
                        if (rtc != null) {
                            RemoteDesktopScreen(
                                deviceId = devId,
                                deviceName = devName,
                                webRtcClient = rtc,
                                eglBase = eglBase,
                                onDisconnect = {
                                    signalingClient?.endSession(devId)
                                    rtc.close()
                                    navController.popBackStack()
                                }
                            )
                        } else {
                            LaunchedEffect(Unit) {
                                Toast.makeText(this@MainActivity, "Connection lost.", Toast.LENGTH_SHORT).show()
                                navController.popBackStack()
                            }
                        }
                    }

                    composable(
                        "files/{deviceId}/{deviceName}",
                        arguments = listOf(
                            navArgument("deviceId") { type = NavType.StringType },
                            navArgument("deviceName") { type = NavType.StringType }
                        )
                    ) { backStackEntry ->
                        val devId = backStackEntry.arguments?.getString("deviceId") ?: ""
                        val devName = backStackEntry.arguments?.getString("deviceName") ?: "Windows PC"

                        val mockDev = Device(
                            id = devId,
                            deviceName = devName,
                            hostname = null,
                            osInfo = "Windows 11",
                            status = "ONLINE",
                            isRemoteEnabled = true,
                            ipAddress = null,
                            lastSeen = "Just now"
                        )
                        FileTransferScreen(device = mockDev, onNavigateBack = { navController.popBackStack() })
                    }

                    composable("settings") {
                        SettingsScreen(
                            tokenManager = tokenManager,
                            onNavigateBack = { navController.popBackStack() }
                        )
                    }
                }
            }
        }
    }

    private fun initiateRemoteSession(device: Device, onSessionReady: () -> Unit) {
        val token = tokenManager.authToken ?: return
        val serverBase = tokenManager.serverUrl
        val wsUrl = serverBase.replace("http://", "ws://").replace("https://", "wss://") + "/ws/signaling"

        CoroutineScope(Dispatchers.Main).launch {
            try {
                Toast.makeText(this@MainActivity, "Requesting remote session...", Toast.LENGTH_SHORT).show()

                val api = ApiService.create(serverBase, tokenManager)
                val sessionResp = api.startSession(mapOf("device_id" to device.id, "client_info" to "Android Mobile"))

                // Initialize WebRTC
                val rtc = WebRtcClient(this@MainActivity, eglBase)
                rtc.createPeerConnection(sessionResp.iceServers)
                webRtcClient = rtc

                // Initialize Signaling
                val sig = SignalingClient(wsUrl, token)
                signalingClient = sig

                sig.onConnected = {
                    sig.requestSession(device.id, sessionResp.sessionId)
                }

                sig.onSessionAccepted = { sessId ->
                    rtc.createOffer { sdpOffer ->
                        sig.sendOffer(sessId, sdpOffer)
                    }
                }

                sig.onSessionRejected = { reason ->
                    Toast.makeText(this@MainActivity, "Session declined: $reason", Toast.LENGTH_LONG).show()
                }

                sig.onAnswerReceived = { sdpAnswer ->
                    rtc.handleRemoteAnswer(sdpAnswer)
                    onSessionReady()
                }

                sig.onIceCandidateReceived = { candJson ->
                    // Parse candidate and add
                    try {
                        val jObj = com.google.gson.JsonParser.parseString(candJson).asJsonObject
                        val sdpMid = jObj.get("sdpMid")?.asString ?: "0"
                        val sdpMLineIndex = jObj.get("sdpMLineIndex")?.asInt ?: 0
                        val candidate = jObj.get("candidate")?.asString ?: ""
                        rtc.addRemoteIceCandidate(sdpMid, sdpMLineIndex, candidate)
                    } catch (e: Exception) {
                        e.printStackTrace()
                    }
                }

                rtc.onIceCandidateGenerated = { candJson ->
                    sig.sendIceCandidate(sessionResp.sessionId, candJson)
                }

                sig.connect()
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Connection failed: ${e.message}", Toast.LENGTH_LONG).show()
            }
        }
    }

    override fun onDestroy() {
        webRtcClient?.close()
        signalingClient?.disconnect()
        eglBase.release()
        super.onDestroy()
    }
}
