package com.remodesk.client.ui.screens

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.view.MotionEvent
import androidx.compose.ui.geometry.Offset
import com.remodesk.client.webrtc.InputEventProtocol

class TouchGestureHandler(
    private val context: Context,
    private val sendInput: (String) -> Unit
) {
    private val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator

    private var initialTouchTime: Long = 0
    private var initialX: Float = 0f
    private var initialY: Float = 0f
    private var lastX: Float = 0f
    private var lastY: Float = 0f
    private var isDragging = false
    private var isTwoFingerScroll = false
    private var initialDistance = 0f
    private var lastTapTime: Long = 0

    fun handleTouchEvent(
        event: MotionEvent,
        viewWidth: Float,
        viewHeight: Float,
        onZoomChange: (Float) -> Unit
    ): Boolean {
        val pointerCount = event.pointerCount

        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                initialTouchTime = System.currentTimeMillis()
                initialX = event.x
                initialY = event.y
                lastX = event.x
                lastY = event.y
                isDragging = false
                isTwoFingerScroll = false
                return true
            }

            MotionEvent.ACTION_POINTER_DOWN -> {
                if (pointerCount == 2) {
                    isTwoFingerScroll = true
                    initialDistance = getFingerDistance(event)
                    lastX = (event.getX(0) + event.getX(1)) / 2f
                    lastY = (event.getY(0) + event.getY(1)) / 2f
                }
                return true
            }

            MotionEvent.ACTION_MOVE -> {
                if (pointerCount == 1) {
                    val dx = event.x - lastX
                    val dy = event.y - lastY
                    val totalDistance = Math.hypot((event.x - initialX).toDouble(), (event.y - initialY).toDouble()).toFloat()

                    if (totalDistance > 15f) {
                        isDragging = true
                        val normX = (event.x / viewWidth).coerceIn(0f, 1f)
                        val normY = (event.y / viewHeight).coerceIn(0f, 1f)
                        sendInput(InputEventProtocol.serializeMouseMove(normX, normY))
                        lastX = event.x
                        lastY = event.y
                    }
                } else if (pointerCount == 2) {
                    // Check for pinch-to-zoom vs two-finger scroll
                    val currentDistance = getFingerDistance(event)
                    val distanceDelta = Math.abs(currentDistance - initialDistance)

                    if (distanceDelta > 40f) {
                        // Pinch to zoom
                        val zoomFactor = currentDistance / initialDistance
                        onZoomChange(zoomFactor)
                    } else {
                        // Two-finger scroll
                        val midY = (event.getY(0) + event.getY(1)) / 2f
                        val midX = (event.getX(0) + event.getX(1)) / 2f
                        val scrollDy = ((lastY - midY) * 1.5f).toInt()
                        val scrollDx = ((lastX - midX) * 1.5f).toInt()

                        if (Math.abs(scrollDy) > 2 || Math.abs(scrollDx) > 2) {
                            sendInput(InputEventProtocol.serializeMouseScroll(scrollDx, scrollDy))
                            lastY = midY
                            lastX = midX
                        }
                    }
                }
                return true
            }

            MotionEvent.ACTION_UP -> {
                val touchDuration = System.currentTimeMillis() - initialTouchTime
                val normX = (event.x / viewWidth).coerceIn(0f, 1f)
                val normY = (event.y / viewHeight).coerceIn(0f, 1f)

                if (!isDragging && !isTwoFingerScroll) {
                    if (touchDuration > 500) {
                        // Long Press -> Right Click
                        triggerHaptic()
                        sendInput(InputEventProtocol.serializeMouseMove(normX, normY))
                        sendInput(InputEventProtocol.serializeMouseButton("right", "click"))
                    } else {
                        // Tap or Double Tap
                        val now = System.currentTimeMillis()
                        if (now - lastTapTime < 280) {
                            // Double Tap -> Double Click
                            sendInput(InputEventProtocol.serializeMouseMove(normX, normY))
                            sendInput(InputEventProtocol.serializeMouseButton("left", "double_click"))
                            lastTapTime = 0
                        } else {
                            // Single Tap -> Left Click
                            sendInput(InputEventProtocol.serializeMouseMove(normX, normY))
                            sendInput(InputEventProtocol.serializeMouseButton("left", "click"))
                            lastTapTime = now
                        }
                    }
                }
                return true
            }

            MotionEvent.ACTION_POINTER_UP -> {
                if (pointerCount <= 2) {
                    isTwoFingerScroll = false
                }
                return true
            }
        }
        return false
    }

    private fun getFingerDistance(event: MotionEvent): Float {
        val x = event.getX(0) - event.getX(1)
        val y = event.getY(0) - event.getY(1)
        return Math.hypot(x.toDouble(), y.toDouble()).toFloat()
    }

    private fun triggerHaptic() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator?.vibrate(VibrationEffect.createOneShot(40, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator?.vibrate(40)
            }
        } catch (e: Exception) {}
    }
}
