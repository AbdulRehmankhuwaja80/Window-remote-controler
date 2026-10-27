package com.remodesk.client.ui.screens

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.view.MotionEvent
import com.remodesk.client.webrtc.InputEventProtocol
import kotlin.math.abs
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min

class TouchGestureHandler(
    private val context: Context,
    private val sendInput: (String) -> Unit
) {
    private val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator

    // Touch tracking for single-finger tap
    private var initialTouchTime: Long = 0L
    private var initialDownX: Float = 0f
    private var initialDownY: Float = 0f
    private var hasMovedBeyondSlop: Boolean = false
    private var isMultiTouch: Boolean = false

    // Multi-touch tracking for pinch-to-zoom & two-finger pan
    private var prevFingerDistance: Float = 0f
    private var prevFocalX: Float = 0f
    private var prevFocalY: Float = 0f

    // Constants
    private val touchSlop = 20f // pixels
    private val maxTapDurationMs = 400L

    companion object {
        const val MIN_ZOOM = 1.0f
        const val MAX_ZOOM = 4.0f

        /**
         * Maps touch coordinates on the Android screen to normalized Windows coordinates (0.0 .. 1.0),
         * accurately accounting for zoom scale, pan offset, view bounds, bitmap dimensions, and fit mode.
         */
        fun mapScreenToWindows(
            screenX: Float,
            screenY: Float,
            viewWidth: Float,
            viewHeight: Float,
            imageWidth: Float,
            imageHeight: Float,
            isFitMode: Boolean,
            zoom: Float,
            panX: Float,
            panY: Float
        ): Pair<Float, Float> {
            if (viewWidth <= 0f || viewHeight <= 0f || imageWidth <= 0f || imageHeight <= 0f) {
                return Pair(0.5f, 0.5f)
            }

            val safeZoom = zoom.coerceIn(MIN_ZOOM, MAX_ZOOM)
            val centerX = viewWidth / 2f
            val centerY = viewHeight / 2f

            // 1. Invert graphicsLayer scale & translation (scaling is centered around view midpoint)
            val unscaledX = centerX + (screenX - centerX - panX) / safeZoom
            val unscaledY = centerY + (screenY - centerY - panY) / safeZoom

            // 2. Compute base image placement within the unscaled view
            val scaleBase = if (isFitMode) {
                min(viewWidth / imageWidth, viewHeight / imageHeight)
            } else {
                max(viewWidth / imageWidth, viewHeight / imageHeight)
            }

            val renderedW = imageWidth * scaleBase
            val renderedH = imageHeight * scaleBase

            val leftBase = (viewWidth - renderedW) / 2f
            val topBase = (viewHeight - renderedH) / 2f

            // 3. Normalize coordinates within the rendered remote desktop area
            val normX = if (renderedW > 0f) ((unscaledX - leftBase) / renderedW).coerceIn(0f, 1f) else 0.5f
            val normY = if (renderedH > 0f) ((unscaledY - topBase) / renderedH).coerceIn(0f, 1f) else 0.5f

            return Pair(normX, normY)
        }

        /**
         * Calculates the maximum permissible pan offset to keep content strictly within boundaries.
         */
        fun calculatePanBounds(
            viewWidth: Float,
            viewHeight: Float,
            imageWidth: Float,
            imageHeight: Float,
            isFitMode: Boolean,
            zoom: Float
        ): Pair<Float, Float> {
            if (viewWidth <= 0f || viewHeight <= 0f || imageWidth <= 0f || imageHeight <= 0f || zoom <= 1.001f) {
                return Pair(0f, 0f)
            }

            val scaleBase = if (isFitMode) {
                min(viewWidth / imageWidth, viewHeight / imageHeight)
            } else {
                max(viewWidth / imageWidth, viewHeight / imageHeight)
            }

            val renderedW = imageWidth * scaleBase
            val renderedH = imageHeight * scaleBase

            val contentW = renderedW * zoom
            val contentH = renderedH * zoom

            val maxPanX = max(0f, (contentW - viewWidth) / 2f)
            val maxPanY = max(0f, (contentH - viewHeight) / 2f)

            return Pair(maxPanX, maxPanY)
        }
    }

    fun handleTouchEvent(
        event: MotionEvent,
        viewWidth: Float,
        viewHeight: Float,
        imageWidth: Float,
        imageHeight: Float,
        isFitMode: Boolean,
        currentZoom: Float,
        currentPanX: Float,
        currentPanY: Float,
        onTransformUpdate: (newZoom: Float, newPanX: Float, newPanY: Float) -> Unit
    ): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                initialTouchTime = System.currentTimeMillis()
                initialDownX = event.x
                initialDownY = event.y
                hasMovedBeyondSlop = false
                isMultiTouch = false
                prevFingerDistance = 0f
                return true
            }

            MotionEvent.ACTION_POINTER_DOWN -> {
                // Second finger touched down: enter multi-touch mode
                isMultiTouch = true
                hasMovedBeyondSlop = true

                if (event.pointerCount >= 2) {
                    val dx = event.getX(0) - event.getX(1)
                    val dy = event.getY(0) - event.getY(1)
                    prevFingerDistance = hypot(dx.toDouble(), dy.toDouble()).toFloat()
                    prevFocalX = (event.getX(0) + event.getX(1)) / 2f
                    prevFocalY = (event.getY(0) + event.getY(1)) / 2f
                }
                return true
            }

            MotionEvent.ACTION_MOVE -> {
                if (event.pointerCount == 1) {
                    if (!isMultiTouch) {
                        val dist = hypot(
                            (event.x - initialDownX).toDouble(),
                            (event.y - initialDownY).toDouble()
                        ).toFloat()

                        if (dist > touchSlop) {
                            hasMovedBeyondSlop = true
                        }
                    }
                } else if (event.pointerCount >= 2) {
                    isMultiTouch = true
                    hasMovedBeyondSlop = true

                    val dx = event.getX(0) - event.getX(1)
                    val dy = event.getY(0) - event.getY(1)
                    val currDistance = hypot(dx.toDouble(), dy.toDouble()).toFloat()
                    val currFocalX = (event.getX(0) + event.getX(1)) / 2f
                    val currFocalY = (event.getY(0) + event.getY(1)) / 2f

                    if (prevFingerDistance > 10f) {
                        val distanceDelta = abs(currDistance - prevFingerDistance)
                        val focalDeltaX = currFocalX - prevFocalX
                        val focalDeltaY = currFocalY - prevFocalY

                        // Distinguish pinch-to-zoom from two-finger panning:
                        // If distance delta is small (< 8px), treat as pure pan to prevent zoom jitter
                        val scaleRatio = if (distanceDelta > 8f) {
                            currDistance / prevFingerDistance
                        } else {
                            1.0f
                        }

                        val targetZoom = (currentZoom * scaleRatio).coerceIn(MIN_ZOOM, MAX_ZOOM)
                        val effectiveScaleRatio = targetZoom / currentZoom

                        val centerX = viewWidth / 2f
                        val centerY = viewHeight / 2f

                        // Keep zoom centered around pinch focal point, and add pan movement
                        var targetPanX = currentPanX * effectiveScaleRatio +
                                (prevFocalX - centerX) * (1f - effectiveScaleRatio) + focalDeltaX
                        var targetPanY = currentPanY * effectiveScaleRatio +
                                (prevFocalY - centerY) * (1f - effectiveScaleRatio) + focalDeltaY

                        // Constrain pan within content boundaries
                        val (maxPanX, maxPanY) = calculatePanBounds(
                            viewWidth, viewHeight, imageWidth, imageHeight, isFitMode, targetZoom
                        )

                        if (targetZoom <= 1.001f) {
                            targetPanX = 0f
                            targetPanY = 0f
                        } else {
                            targetPanX = targetPanX.coerceIn(-maxPanX, maxPanX)
                            targetPanY = targetPanY.coerceIn(-maxPanY, maxPanY)
                        }

                        onTransformUpdate(targetZoom, targetPanX, targetPanY)
                    }

                    prevFingerDistance = currDistance
                    prevFocalX = currFocalX
                    prevFocalY = currFocalY
                }
                return true
            }

            MotionEvent.ACTION_POINTER_UP -> {
                // One finger lifted from multi-touch
                prevFingerDistance = 0f
                return true
            }

            MotionEvent.ACTION_UP -> {
                val touchDuration = System.currentTimeMillis() - initialTouchTime

                // A single tap must be stationary, single-touch, and within tap duration threshold
                if (!isMultiTouch && !hasMovedBeyondSlop && touchDuration < maxTapDurationMs) {
                    val (normX, normY) = mapScreenToWindows(
                        screenX = event.x,
                        screenY = event.y,
                        viewWidth = viewWidth,
                        viewHeight = viewHeight,
                        imageWidth = imageWidth,
                        imageHeight = imageHeight,
                        isFitMode = isFitMode,
                        zoom = currentZoom,
                        panX = currentPanX,
                        panY = currentPanY
                    )

                    // Position pointer at tapped location and perform exactly one Windows left-click
                    triggerHaptic()
                    sendInput(InputEventProtocol.serializeMouseMove(normX, normY))
                    sendInput(InputEventProtocol.serializeMouseButton("left", "click"))
                }

                // Reset state
                isMultiTouch = false
                hasMovedBeyondSlop = false
                prevFingerDistance = 0f
                return true
            }

            MotionEvent.ACTION_CANCEL -> {
                isMultiTouch = false
                hasMovedBeyondSlop = false
                prevFingerDistance = 0f
                return true
            }
        }
        return false
    }

    private fun triggerHaptic() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator?.vibrate(VibrationEffect.createOneShot(35, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator?.vibrate(35)
            }
        } catch (_: Exception) {}
    }
}
