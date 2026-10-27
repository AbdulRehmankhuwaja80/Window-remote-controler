package com.remodesk.client.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.graphics.BitmapFactory
import android.view.MotionEvent
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInteropFilter
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.layout.onSizeChanged
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.remodesk.client.data.TokenManager
import com.remodesk.client.network.SignalingClient
import com.remodesk.client.ui.theme.*
import com.remodesk.client.webrtc.InputEventProtocol
import com.remodesk.client.webrtc.WebRtcClient
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import org.webrtc.PeerConnection
import java.nio.charset.StandardCharsets

enum class SessionConnectionState {
    CONNECTING,
    CONNECTED,
    RECONNECTING,
    PAUSED,
    DISCONNECTED,
    FAILED
}

@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun RemoteDesktopScreen(
    deviceId: String,
    deviceName: String,
    webRtcClient: WebRtcClient,
    signalingClient: SignalingClient? = null,
    tokenManager: TokenManager? = null,
    onReconnect: (() -> Unit)? = null,
    onDisconnect: () -> Unit
) {
    val context = LocalContext.current
    val clipboardManager = remember { context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager }
    val coroutineScope = rememberCoroutineScope()

    var connectionState by remember { mutableStateOf(SessionConnectionState.CONNECTING) }
    var reconnectAttempts by remember { mutableIntStateOf(0) }
    var reconnectCountdown by remember { mutableIntStateOf(0) }
    var statusMessage by remember { mutableStateOf("Connecting to $deviceName...") }

    var isTouchpadMode by remember { mutableStateOf(false) }
    var isKeyboardVisible by remember { mutableStateOf(false) }
    var isFitMode by remember { mutableStateOf(true) }
    var latencyMs by remember { mutableLongStateOf(0L) }
    var zoomScale by remember { mutableFloatStateOf(1.0f) }
    var panOffsetX by remember { mutableFloatStateOf(0f) }
    var panOffsetY by remember { mutableFloatStateOf(0f) }
    var viewerWidth by remember { mutableFloatStateOf(0f) }
    var viewerHeight by remember { mutableFloatStateOf(0f) }
    var currentFrame by remember { mutableStateOf<ImageBitmap?>(null) }
    var frameCount by remember { mutableIntStateOf(0) }

    val maxReconnect = tokenManager?.maxReconnectAttempts ?: 5
    val autoReconnect = tokenManager?.autoReconnect ?: true
    val reconnectTimeout = tokenManager?.reconnectTimeoutSeconds ?: 30

    val gestureHandler = remember {
        TouchGestureHandler(context) { msg ->
            webRtcClient.sendInputMessage(msg)
        }
    }

    fun triggerReconnectFlow() {
        if (!autoReconnect || reconnectAttempts >= maxReconnect) {
            connectionState = SessionConnectionState.FAILED
            statusMessage = "Connection failed after $reconnectAttempts attempts."
            return
        }

        reconnectAttempts++
        connectionState = SessionConnectionState.RECONNECTING
        zoomScale = 1.0f
        panOffsetX = 0f
        panOffsetY = 0f
        val backoffSeconds = minOf(1 shl (reconnectAttempts - 1), reconnectTimeout)
        reconnectCountdown = backoffSeconds
        statusMessage = "Reconnecting in ${backoffSeconds}s (attempt $reconnectAttempts of $maxReconnect)..."

        coroutineScope.launch {
            for (sec in backoffSeconds downTo 1) {
                reconnectCountdown = sec
                statusMessage = "Reconnecting in ${sec}s (attempt $reconnectAttempts of $maxReconnect)..."
                delay(1000L)
            }
            onReconnect?.invoke()
        }
    }

    // Monitor Incoming frames, peer connection state & signaling
    DisposableEffect(webRtcClient, signalingClient) {
        val startTime = System.currentTimeMillis()

        webRtcClient.onFrameReceived = { jpegBytes ->
            try {
                val bmp = BitmapFactory.decodeByteArray(jpegBytes, 0, jpegBytes.size)
                if (bmp != null) {
                    currentFrame = bmp.asImageBitmap()
                    if (connectionState != SessionConnectionState.CONNECTED) {
                        connectionState = SessionConnectionState.CONNECTED
                        reconnectAttempts = 0
                    }
                    frameCount++
                    latencyMs = ((System.currentTimeMillis() - startTime) / maxOf(frameCount, 1)).coerceAtLeast(12L)
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }

        webRtcClient.onConnectionStateChange = { pcState ->
            coroutineScope.launch {
                when (pcState) {
                    PeerConnection.PeerConnectionState.CONNECTED -> {
                        connectionState = SessionConnectionState.CONNECTED
                        reconnectAttempts = 0
                    }
                    PeerConnection.PeerConnectionState.DISCONNECTED -> {
                        triggerReconnectFlow()
                    }
                    PeerConnection.PeerConnectionState.FAILED -> {
                        triggerReconnectFlow()
                    }
                    PeerConnection.PeerConnectionState.CLOSED -> {
                        connectionState = SessionConnectionState.DISCONNECTED
                    }
                    else -> {}
                }
            }
        }

        signalingClient?.onSessionTerminated = { reason ->
            coroutineScope.launch {
                if (reason.contains("pause", ignoreCase = true)) {
                    connectionState = SessionConnectionState.PAUSED
                    statusMessage = "Remote control paused by host laptop."
                } else {
                    connectionState = SessionConnectionState.DISCONNECTED
                    statusMessage = "Session terminated: $reason"
                }
            }
        }

        // Incoming Clipboard Sync from Windows Host
        signalingClient?.onClipboardReceived = { text ->
            coroutineScope.launch {
                if (text.isNotEmpty()) {
                    val clip = ClipData.newPlainText("RemoDesk", text)
                    clipboardManager.setPrimaryClip(clip)
                    Toast.makeText(context, "Clipboard synced from laptop (${text.length} chars)", Toast.LENGTH_SHORT).show()
                }
            }
        }

        onDispose {
            webRtcClient.onFrameReceived = null
            webRtcClient.onConnectionStateChange = null
            if (signalingClient != null) {
                signalingClient.onSessionTerminated = null
                signalingClient.onClipboardReceived = null
            }
        }
    }

    Scaffold(
        containerColor = DarkNavyBackground,
        content = { innerPadding ->
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(innerPadding)
            ) {
                // Desktop Frame Display
                if (currentFrame != null) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .clipToBounds()
                            .onSizeChanged { size ->
                                viewerWidth = size.width.toFloat()
                                viewerHeight = size.height.toFloat()
                            }
                            .pointerInteropFilter { motionEvent ->
                                if (!isTouchpadMode && connectionState == SessionConnectionState.CONNECTED) {
                                    val bmp = currentFrame!!
                                    val vw = if (viewerWidth > 0f) viewerWidth else context.resources.displayMetrics.widthPixels.toFloat()
                                    val vh = if (viewerHeight > 0f) viewerHeight else context.resources.displayMetrics.heightPixels.toFloat()
                                    gestureHandler.handleTouchEvent(
                                        event = motionEvent,
                                        viewWidth = vw,
                                        viewHeight = vh,
                                        imageWidth = bmp.width.toFloat(),
                                        imageHeight = bmp.height.toFloat(),
                                        isFitMode = isFitMode,
                                        currentZoom = zoomScale,
                                        currentPanX = panOffsetX,
                                        currentPanY = panOffsetY
                                    ) { newZoom, newPanX, newPanY ->
                                        zoomScale = newZoom
                                        panOffsetX = newPanX
                                        panOffsetY = newPanY
                                    }
                                } else {
                                    false
                                }
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Image(
                            bitmap = currentFrame!!,
                            contentDescription = "Remote Desktop Stream",
                            modifier = Modifier
                                .fillMaxSize()
                                .graphicsLayer {
                                    scaleX = zoomScale
                                    scaleY = zoomScale
                                    translationX = panOffsetX
                                    translationY = panOffsetY
                                },
                            contentScale = if (isFitMode) ContentScale.Fit else ContentScale.Crop
                        )
                    }
                }

                // Overlay for non-connected states (CONNECTING, RECONNECTING, PAUSED, FAILED, DISCONNECTED)
                if (connectionState != SessionConnectionState.CONNECTED) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(DarkNavyBackground.copy(alpha = if (currentFrame != null) 0.85f else 1.0f)),
                        contentAlignment = Alignment.Center
                    ) {
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(32.dp),
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(containerColor = CharcoalSurface)
                        ) {
                            Column(
                                modifier = Modifier
                                    .padding(24.dp)
                                    .fillMaxWidth(),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.spacedBy(16.dp)
                            ) {
                                when (connectionState) {
                                    SessionConnectionState.CONNECTING -> {
                                        CircularProgressIndicator(color = ElectricBluePrimary, modifier = Modifier.size(48.dp))
                                        Text("Connecting to $deviceName...", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                                        Text("Negotiating WebRTC stream & STUN/TURN relays", color = TextSecondary, style = MaterialTheme.typography.bodySmall)
                                    }
                                    SessionConnectionState.RECONNECTING -> {
                                        CircularProgressIndicator(color = StatusWarning, modifier = Modifier.size(48.dp))
                                        Text("Reconnecting...", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                                        Text(statusMessage, color = TextSecondary, style = MaterialTheme.typography.bodySmall)
                                    }
                                    SessionConnectionState.PAUSED -> {
                                        Icon(Icons.Default.PauseCircleOutline, contentDescription = null, tint = StatusWarning, modifier = Modifier.size(54.dp))
                                        Text("Remote Access Paused", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                                        Text("The laptop user has paused remote control access. Waiting for host to resume...", color = TextSecondary, style = MaterialTheme.typography.bodySmall)
                                    }
                                    SessionConnectionState.FAILED -> {
                                        Icon(Icons.Default.ErrorOutline, contentDescription = null, tint = StatusError, modifier = Modifier.size(54.dp))
                                        Text("Connection Failed", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                                        Text("Could not reach $deviceName. Please check that host is running and connected.", color = TextSecondary, style = MaterialTheme.typography.bodySmall)
                                        Spacer(modifier = Modifier.height(8.dp))
                                        Button(
                                            onClick = {
                                                reconnectAttempts = 0
                                                connectionState = SessionConnectionState.CONNECTING
                                                onReconnect?.invoke()
                                            },
                                            colors = ButtonDefaults.buttonColors(containerColor = ElectricBluePrimary)
                                        ) {
                                            Text("Retry Connection")
                                        }
                                    }
                                    SessionConnectionState.DISCONNECTED -> {
                                        Icon(Icons.Default.PowerSettingsNew, contentDescription = null, tint = TextSecondary, modifier = Modifier.size(54.dp))
                                        Text("Session Ended", color = TextPrimary, style = MaterialTheme.typography.titleMedium)
                                        Text(statusMessage, color = TextSecondary, style = MaterialTheme.typography.bodySmall)
                                    }
                                    else -> {}
                                }
                            }
                        }
                    }
                }

                // Top Floating Status HUD
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 16.dp, start = 16.dp, end = 16.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Device & Latency Card
                    Surface(
                        shape = RoundedCornerShape(20.dp),
                        color = CharcoalSurface.copy(alpha = 0.88f),
                        tonalElevation = 4.dp
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            val dotColor = when (connectionState) {
                                SessionConnectionState.CONNECTED -> StatusOnline
                                SessionConnectionState.CONNECTING -> ElectricBluePrimary
                                SessionConnectionState.RECONNECTING -> StatusWarning
                                SessionConnectionState.PAUSED -> StatusWarning
                                SessionConnectionState.FAILED -> StatusError
                                SessionConnectionState.DISCONNECTED -> TextSecondary
                            }
                            Box(
                                modifier = Modifier
                                    .size(10.dp)
                                    .background(dotColor, shape = CircleShape)
                            )
                            Text(
                                text = deviceName,
                                style = MaterialTheme.typography.labelMedium,
                                color = TextPrimary
                            )
                            if (connectionState == SessionConnectionState.CONNECTED) {
                                Text(text = "•", color = TextSecondary)
                                Text(
                                    text = "${latencyMs}ms",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = if (latencyMs < 60) StatusOnline else StatusWarning
                                )
                            } else {
                                Text(
                                    text = "• ${connectionState.name}",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = dotColor
                                )
                            }
                        }
                    }

                    // Disconnect Button
                    IconButton(
                        onClick = onDisconnect,
                        modifier = Modifier
                            .background(StatusError.copy(alpha = 0.9f), shape = CircleShape)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Close,
                            contentDescription = "Disconnect",
                            tint = Color.White
                        )
                    }
                }

                // Bottom Controls Layout
                Column(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .fillMaxWidth()
                ) {
                    // Virtual Touchpad if active
                    if (isTouchpadMode) {
                        VirtualTouchpad(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(200.dp),
                            sendInput = { msg: String -> webRtcClient.sendInputMessage(msg) }
                        )
                    }

                    // On-Screen Keyboard
                    if (isKeyboardVisible) {
                        OnScreenKeyboardBar(
                            modifier = Modifier.fillMaxWidth(),
                            sendInput = { msg: String -> webRtcClient.sendInputMessage(msg) }
                        )
                    }

                    // Compact Toolbar
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        color = CharcoalSurface.copy(alpha = 0.92f),
                        tonalElevation = 8.dp
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 8.dp, vertical = 6.dp),
                            horizontalArrangement = Arrangement.SpaceEvenly,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            // Touchpad toggle
                            IconButton(onClick = { isTouchpadMode = !isTouchpadMode }) {
                                Icon(
                                    imageVector = Icons.Default.TouchApp,
                                    contentDescription = "Toggle Touchpad",
                                    tint = if (isTouchpadMode) ElectricBluePrimary else TextSecondary
                                )
                            }

                            // Keyboard toggle
                            IconButton(onClick = { isKeyboardVisible = !isKeyboardVisible }) {
                                Icon(
                                    imageVector = Icons.Default.Keyboard,
                                    contentDescription = "Toggle Keyboard",
                                    tint = if (isKeyboardVisible) ElectricBluePrimary else TextSecondary
                                )
                            }

                            // Fit/Fill toggle
                            IconButton(onClick = {
                                isFitMode = !isFitMode
                                zoomScale = 1.0f
                                panOffsetX = 0f
                                panOffsetY = 0f
                            }) {
                                Icon(
                                    imageVector = if (isFitMode) Icons.Default.FitScreen else Icons.Default.Fullscreen,
                                    contentDescription = "Toggle Fit/Fill",
                                    tint = TextSecondary
                                )
                            }

                            // Clipboard Paste with Strict Validation (max 64KB, text-only, confirmation)
                            IconButton(onClick = {
                                val clip = clipboardManager.primaryClip
                                if (clip == null || clip.itemCount == 0) {
                                    Toast.makeText(context, "Mobile clipboard is empty.", Toast.LENGTH_SHORT).show()
                                    return@IconButton
                                }

                                val textItem = clip.getItemAt(0)
                                val text = textItem.text?.toString()

                                if (text.isNullOrEmpty()) {
                                    Toast.makeText(context, "Clipboard does not contain plain text.", Toast.LENGTH_SHORT).show()
                                    return@IconButton
                                }

                                val utf8Bytes = text.toByteArray(StandardCharsets.UTF_8)
                                val maxBytes = 64 * 1024 // 64 KB limit
                                if (utf8Bytes.size > maxBytes) {
                                    Toast.makeText(context, "Clipboard content exceeds 64KB limit (${utf8Bytes.size / 1024} KB).", Toast.LENGTH_LONG).show()
                                    return@IconButton
                                }

                                val sanitizedJson = text
                                    .replace("\\", "\\\\")
                                    .replace("\"", "\\\"")
                                    .replace("\r", "\\r")
                                    .replace("\n", "\\n")
                                    .replace("\t", "\\t")

                                webRtcClient.sendInputMessage("{\"type\":\"clipboard_sync\",\"text\":\"$sanitizedJson\"}")
                                Toast.makeText(context, "Pasted ${text.length} characters to laptop.", Toast.LENGTH_SHORT).show()
                            }) {
                                Icon(
                                    imageVector = Icons.Default.ContentPaste,
                                    contentDescription = "Paste Clipboard to Laptop",
                                    tint = CyanSecondary
                                )
                            }
                        }
                    }
                }
            }
        }
    )
}
