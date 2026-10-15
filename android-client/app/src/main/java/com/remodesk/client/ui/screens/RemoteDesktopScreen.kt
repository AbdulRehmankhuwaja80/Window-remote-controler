package com.remodesk.client.ui.screens

import android.content.ClipboardManager
import android.content.Context
import android.view.MotionEvent
import android.widget.Toast
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
import androidx.compose.ui.input.pointer.pointerInteropFilter
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.remodesk.client.ui.theme.*
import com.remodesk.client.webrtc.InputEventProtocol
import com.remodesk.client.webrtc.WebRtcClient
import org.webrtc.EglBase
import org.webrtc.RendererCommon
import org.webrtc.SurfaceViewRenderer

@OptIn(ExperimentalComposeUiApi::class)
@Composable
fun RemoteDesktopScreen(
    deviceId: String,
    deviceName: String,
    webRtcClient: WebRtcClient,
    eglBase: EglBase,
    onDisconnect: () -> Unit
) {
    val context = LocalContext.current
    val clipboardManager = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager

    var isTouchpadMode by remember { mutableStateOf(false) }
    var isKeyboardVisible by remember { mutableStateOf(false) }
    var isFitMode by remember { mutableStateOf(true) }
    var latencyMs by remember { mutableStateOf(32L) }
    var zoomScale by remember { mutableStateOf(1.0f) }

    val gestureHandler = remember {
        TouchGestureHandler(context) { msg ->
            webRtcClient.sendInputMessage(msg)
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
                // Video Surface
                AndroidView(
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
                    factory = { ctx ->
                        SurfaceViewRenderer(ctx).apply {
                            init(eglBase.eglBaseContext, null)
                            setEnableHardwareScaler(true)
                            setScalingType(
                                if (isFitMode) RendererCommon.ScalingType.SCALE_ASPECT_FIT
                                else RendererCommon.ScalingType.SCALE_ASPECT_FILL
                            )
                            webRtcClient.onRemoteVideoTrackReceived = { track ->
                                track.addSink(this)
                            }
                        }
                    },
                    update = { view ->
                        view.setScalingType(
                            if (isFitMode) RendererCommon.ScalingType.SCALE_ASPECT_FIT
                            else RendererCommon.ScalingType.SCALE_ASPECT_FILL
                        )
                    }
                )

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
                                    .background(StatusOnline, shape = CircleShape)
                            )
                            Text(
                                text = deviceName,
                                style = MaterialTheme.typography.labelMedium,
                                color = TextPrimary
                            )
                            Text(
                                text = "•",
                                color = TextSecondary
                            )
                            Text(
                                text = "${latencyMs}ms",
                                style = MaterialTheme.typography.labelSmall,
                                color = StatusOnline
                            )
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

                // Bottom Controls Layout (Keyboard / Touchpad / Toolbar)
                Column(
                    modifier = Modifier
                        .align(Alignment.BottomCenter)
                        .fillMaxWidth()
                ) {
                    // Virtual Touchpad if active
                    if (isTouchpadMode) {
                        VirtualTouchpad { msg ->
                            webRtcClient.sendInputMessage(msg)
                        }
                    }

                    // On-Screen Keyboard if active
                    if (isKeyboardVisible) {
                        OnScreenKeyboardBar { msg ->
                            webRtcClient.sendInputMessage(msg)
                        }
                    }

                    // Compact Floating Toolbar
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(60.dp),
                        color = CharcoalSurface.copy(alpha = 0.95f),
                        tonalElevation = 8.dp
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxSize()
                                .padding(horizontal = 16.dp),
                            horizontalArrangement = Arrangement.SpaceEvenly,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            // Toggle Keyboard
                            IconButton(onClick = { isKeyboardVisible = !isKeyboardVisible }) {
                                Icon(
                                    imageVector = Icons.Default.Keyboard,
                                    contentDescription = "Keyboard",
                                    tint = if (isKeyboardVisible) ElectricBluePrimary else TextSecondary
                                )
                            }

                            // Toggle Touchpad / Direct Mode
                            IconButton(onClick = { isTouchpadMode = !isTouchpadMode }) {
                                Icon(
                                    imageVector = if (isTouchpadMode) Icons.Default.TouchApp else Icons.Default.Mouse,
                                    contentDescription = "Touchpad",
                                    tint = if (isTouchpadMode) ElectricBluePrimary else TextSecondary
                                )
                            }

                            // Toggle Aspect Ratio Fit/Fill
                            IconButton(onClick = { isFitMode = !isFitMode }) {
                                Icon(
                                    imageVector = if (isFitMode) Icons.Default.FitScreen else Icons.Default.Fullscreen,
                                    contentDescription = "Aspect Ratio",
                                    tint = TextSecondary
                                )
                            }

                            // Sync Phone Clipboard to Windows
                            IconButton(onClick = {
                                val clipData = clipboardManager.primaryClip
                                if (clipData != null && clipData.itemCount > 0) {
                                    val text = clipData.getItemAt(0).text.toString()
                                    webRtcClient.sendInputMessage(InputEventProtocol.serializeClipboardSync(text))
                                    Toast.makeText(context, "Clipboard synced to PC", Toast.LENGTH_SHORT).show()
                                } else {
                                    Toast.makeText(context, "Clipboard is empty", Toast.LENGTH_SHORT).show()
                                }
                            }) {
                                Icon(
                                    imageVector = Icons.Default.ContentPaste,
                                    contentDescription = "Clipboard Sync",
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
