package com.remodesk.client.ui.screens

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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.input.pointer.pointerInteropFilter
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.remodesk.client.ui.theme.*
import com.remodesk.client.webrtc.InputEventProtocol
import com.remodesk.client.webrtc.WebRtcClient

@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun RemoteDesktopScreen(
    deviceId: String,
    deviceName: String,
    webRtcClient: WebRtcClient,
    onDisconnect: () -> Unit
) {
    val context = LocalContext.current
    val clipboardManager = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager

    var isTouchpadMode by remember { mutableStateOf(false) }
    var isKeyboardVisible by remember { mutableStateOf(false) }
    var isFitMode by remember { mutableStateOf(true) }
    var latencyMs by remember { mutableStateOf(0L) }
    var zoomScale by remember { mutableStateOf(1.0f) }
    var isStreamReady by remember { mutableStateOf(false) }
    var currentFrame by remember { mutableStateOf<ImageBitmap?>(null) }
    var frameCount by remember { mutableIntStateOf(0) }

    val gestureHandler = remember {
        TouchGestureHandler(context) { msg ->
            webRtcClient.sendInputMessage(msg)
        }
    }

    // Wire up frame receiving
    DisposableEffect(webRtcClient) {
        val startTime = System.currentTimeMillis()
        webRtcClient.onFrameReceived = { jpegBytes ->
            try {
                val bmp = BitmapFactory.decodeByteArray(jpegBytes, 0, jpegBytes.size)
                if (bmp != null) {
                    currentFrame = bmp.asImageBitmap()
                    if (!isStreamReady) isStreamReady = true
                    frameCount++
                    latencyMs = (System.currentTimeMillis() - startTime) / maxOf(frameCount, 1).toLong()
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
        onDispose {
            webRtcClient.onFrameReceived = null
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
                    Image(
                        bitmap = currentFrame!!,
                        contentDescription = "Remote Desktop",
                        modifier = Modifier
                            .fillMaxSize()
                            .pointerInteropFilter { motionEvent ->
                                if (!isTouchpadMode) {
                                    val width = context.resources.displayMetrics.widthPixels.toFloat()
                                    val height = context.resources.displayMetrics.heightPixels.toFloat()
                                    gestureHandler.handleTouchEvent(motionEvent, width, height) { factor ->
                                        zoomScale = (zoomScale * factor).coerceIn(1.0f, 4.0f)
                                    }
                                } else {
                                    false
                                }
                            },
                        contentScale = if (isFitMode) ContentScale.Fit else ContentScale.Crop
                    )
                }

                // Connecting overlay
                if (!isStreamReady) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(DarkNavyBackground),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            CircularProgressIndicator(
                                color = ElectricBluePrimary,
                                modifier = Modifier.size(52.dp),
                                strokeWidth = 4.dp
                            )
                            Text(
                                text = "Connecting to $deviceName...",
                                color = TextPrimary,
                                style = MaterialTheme.typography.titleMedium
                            )
                            Text(
                                text = "Establishing desktop stream",
                                color = TextSecondary,
                                style = MaterialTheme.typography.bodySmall
                            )
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
                        color = CharcoalSurface.copy(alpha = 0.85f),
                        tonalElevation = 4.dp
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(10.dp)
                                    .background(if (isStreamReady) StatusOnline else StatusWarning, shape = CircleShape)
                            )
                            Text(
                                text = deviceName,
                                style = MaterialTheme.typography.labelMedium,
                                color = TextPrimary
                            )
                            if (isStreamReady) {
                                Text(text = "•", color = TextSecondary)
                                Text(
                                    text = "LIVE",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = StatusOnline
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
                        color = CharcoalSurface.copy(alpha = 0.9f),
                        tonalElevation = 8.dp
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 8.dp, vertical = 4.dp),
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
                            IconButton(onClick = { isFitMode = !isFitMode }) {
                                Icon(
                                    imageVector = if (isFitMode) Icons.Default.FitScreen else Icons.Default.Fullscreen,
                                    contentDescription = "Toggle Fit/Fill",
                                    tint = TextSecondary
                                )
                            }

                            // Clipboard paste
                            IconButton(onClick = {
                                val clip = clipboardManager.primaryClip
                                if (clip != null && clip.itemCount > 0) {
                                    val text = clip.getItemAt(0).text?.toString()
                                    if (!text.isNullOrEmpty()) {
                                        webRtcClient.sendInputMessage(
                                            "{\"type\":\"text_input\",\"text\":\"${text.replace("\"", "\\\"").replace("\n", "\\n")}\"}"
                                        )
                                        Toast.makeText(context, "Pasted to laptop", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            }) {
                                Icon(
                                    imageVector = Icons.Default.ContentPaste,
                                    contentDescription = "Paste Clipboard",
                                    tint = TextSecondary
                                )
                            }
                        }
                    }
                }
            }
        }
    )
}
