package com.remodesk.client.ui.screens

import android.content.Context
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.VibrationEffect
import android.os.Vibrator
import android.view.MotionEvent
import com.remodesk.client.webrtc.InputEventProtocol
import kotlin.math.abs
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min

/**
 * TouchGestureHandler — Direct touch-to-remote-desktop interaction.
 *
 * Gesture mapping:
 *   Single tap          → Windows left-click at tapped coordinates
 *   Double-tap          → Windows double-click (opens apps, folders, files)
 *   Long-press          → Windows right-click (context menu)
 *   Two-finger pinch    → Zoom Android view (1×–4×, focal-point centred)
 *   Two-finger pan      → Pan the zoomed view (boundary clamped)
 *   Two-finger scroll   → Windows scroll wheel (vertical)
 *
 * The virtual touchpad has been removed; all interaction is direct.
 */
class TouchGestureHandler(
    private val context: Context,
    private val sendInput: (String) -> Unit
) {
    private val vibrator = context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
    private val mainHandler = Handler(Looper.getMainLooper())

    // ── Single-finger tap tracking ─────────────────────────────────────────────
    private var initialTouchTime: Long = 0L
    private var initialDownX: Float = 0f
    private var initialDownY: Float = 0f
    private var hasMovedBeyondSlop: Boolean = false
    private var isMultiTouch: Boolean = false

    // ── Double-tap detection ───────────────────────────────────────────────────
    private var lastTapTime: Long = 0L
    private var lastTapX: Float = 0f
    private var lastTapY: Float = 0f

    // ── Long-press detection ───────────────────────────────────────────────────
    private var longPressRunnable: Runnable? = null
    private var longPressFired: Boolean = false

    // Snapshot of view/image dims captured at ACTION_DOWN for the long-press closure
    private var lpViewWidth: Float = 0f
    private var lpViewHeight: Float = 0f
    private var lpImageWidth: Float = 0f
    private var lpImageHeight: Float = 0f
    private var lpIsFitMode: Boolean = true
    private var lpZoom: Float = 1f
    private var lpPanX: Float = 0f
    private var lpPanY: Float = 0f

    // ── Multi-touch tracking for pinch/pan/scroll ──────────────────────────────
    private var prevFingerDistance: Float = 0f
    private var prevFocalX: Float = 0f
    private var prevFocalY: Float = 0f

    // Two-finger scroll: accumulated vertical delta
    private var scrollAccumY: Float = 0f

    // ── Constants ──────────────────────────────────────────────────────────────
    private val touchSlop = 20f            // px — movement that cancels a tap
    private val maxTapDurationMs = 400L   // ms — max contact time for a tap
    private val doubleTapWindowMs = 350L  // ms — max gap between two taps for double-tap
    private val doubleTapSlopPx = 60f     // px — max distance between two tap positions
    private val longPressDelayMs = 500L   // ms — hold still this long → right-click
    private val scrollTickPx = 40f        // px of two-finger movement per scroll tick
    private val scrollWheelAmount = -120  // Windows WHEEL_DELTA per tick (negative = down)

    companion object {
        const val MIN_ZOOM = 1.0f
        const val MAX_ZOOM = 4.0f

        /**
         * Maps touch coordinates on the Android screen to normalised Windows coordinates [0, 1],
         * accounting for zoom, pan, view size, bitmap size, and fit/fill mode.
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

            // Invert graphicsLayer scale & translation (scaling is centred around view midpoint)
            val unscaledX = centerX + (screenX - centerX - panX) / safeZoom
            val unscaledY = centerY + (screenY - centerY - panY) / safeZoom

            // Base image placement within the unscaled view
            val scaleBase = if (isFitMode) {
                min(viewWidth / imageWidth, viewHeight / imageHeight)
            } else {
                max(viewWidth / imageWidth, viewHeight / imageHeight)
            }

            val renderedW = imageWidth * scaleBase
            val renderedH = imageHeight * scaleBase
            val leftBase = (viewWidth - renderedW) / 2f
            val topBase  = (viewHeight - renderedH) / 2f

            val normX = if (renderedW > 0f) ((unscaledX - leftBase) / renderedW).coerceIn(0f, 1f) else 0.5f
            val normY = if (renderedH > 0f) ((unscaledY - topBase) / renderedH).coerceIn(0f, 1f) else 0.5f

            return Pair(normX, normY)
        }

        /**
         * Returns the maximum pan offset that keeps the zoomed content within the view boundaries.
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
            val contentW  = renderedW * zoom
            val contentH  = renderedH * zoom

            return Pair(
                max(0f, (contentW - viewWidth) / 2f),
                max(0f, (contentH - viewHeight) / 2f)
            )
        }
    }

    // ── Public entry point ─────────────────────────────────────────────────────

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

            // ── First finger down ──────────────────────────────────────────────
            MotionEvent.ACTION_DOWN -> {
                initialTouchTime = System.currentTimeMillis()
                initialDownX     = event.x
                initialDownY     = event.y
                hasMovedBeyondSlop = false
                isMultiTouch     = false
                longPressFired   = false
                scrollAccumY     = 0f
                prevFingerDistance = 0f

                // Snapshot view context for the long-press closure
                lpViewWidth  = viewWidth
                lpViewHeight = viewHeight
                lpImageWidth = imageWidth
                lpImageHeight = imageHeight
                lpIsFitMode  = isFitMode
                lpZoom       = currentZoom
                lpPanX       = currentPanX
                lpPanY       = currentPanY

                // Arm the long-press timer
                val lpRunnable = Runnable {
                    // Fire only if still a single, stationary touch
                    if (!isMultiTouch && !hasMovedBeyondSlop && !longPressFired) {
                        longPressFired = true
                        val (normX, normY) = mapScreenToWindows(
                            screenX     = initialDownX,
                            screenY     = initialDownY,
                            viewWidth   = lpViewWidth,
                            viewHeight  = lpViewHeight,
                            imageWidth  = lpImageWidth,
                            imageHeight = lpImageHeight,
                            isFitMode   = lpIsFitMode,
                            zoom        = lpZoom,
                            panX        = lpPanX,
                            panY        = lpPanY
                        )
                        triggerHaptic(longPress = true)
                        sendInput(InputEventProtocol.serializeMouseMove(normX, normY))
                        sendInput(InputEventProtocol.serializeMouseButton("right", "click"))
                    }
                }
                longPressRunnable = lpRunnable
                mainHandler.postDelayed(lpRunnable, longPressDelayMs)

                return true
            }

            // ── Second (or more) finger touches down ──────────────────────────
            MotionEvent.ACTION_POINTER_DOWN -> {
                isMultiTouch       = true
                hasMovedBeyondSlop = true
                cancelLongPress()

                if (event.pointerCount >= 2) {
                    val dx = event.getX(0) - event.getX(1)
                    val dy = event.getY(0) - event.getY(1)
                    prevFingerDistance = hypot(dx.toDouble(), dy.toDouble()).toFloat()
                    prevFocalX = (event.getX(0) + event.getX(1)) / 2f
                    prevFocalY = (event.getY(0) + event.getY(1)) / 2f
                    scrollAccumY = 0f
                }
                return true
            }

            // ── Fingers move ───────────────────────────────────────────────────
            MotionEvent.ACTION_MOVE -> {
                if (event.pointerCount == 1) {
                    if (!isMultiTouch) {
                        val dist = hypot(
                            (event.x - initialDownX).toDouble(),
                            (event.y - initialDownY).toDouble()
                        ).toFloat()
                        if (dist > touchSlop) {
                            hasMovedBeyondSlop = true
                            cancelLongPress()
                        }
                    }

                } else if (event.pointerCount >= 2) {
                    isMultiTouch       = true
                    hasMovedBeyondSlop = true

                    val dx          = event.getX(0) - event.getX(1)
                    val dy          = event.getY(0) - event.getY(1)
                    val currDistance = hypot(dx.toDouble(), dy.toDouble()).toFloat()
                    val currFocalX   = (event.getX(0) + event.getX(1)) / 2f
                    val currFocalY   = (event.getY(0) + event.getY(1)) / 2f

                    if (prevFingerDistance > 10f) {
                        val distanceDelta = abs(currDistance - prevFingerDistance)
                        val focalDeltaX   = currFocalX - prevFocalX
                        val focalDeltaY   = currFocalY - prevFocalY

                        // ── Distinguish pinch vs. two-finger pan/scroll ────────
                        // If finger spread changes by more than 8 px → zoom gesture.
                        // Otherwise treat as pan + potential scroll.
                        val isZooming = distanceDelta > 8f

                        if (isZooming) {
                            // Pinch-to-zoom with focal-point invariance
                            scrollAccumY = 0f
                            val scaleRatio  = currDistance / prevFingerDistance
                            val targetZoom  = (currentZoom * scaleRatio).coerceIn(MIN_ZOOM, MAX_ZOOM)
                            val effectiveScaleRatio = targetZoom / currentZoom
                            val centerX = viewWidth / 2f
                            val centerY = viewHeight / 2f

                            var targetPanX = currentPanX * effectiveScaleRatio +
                                    (prevFocalX - centerX) * (1f - effectiveScaleRatio) + focalDeltaX
                            var targetPanY = currentPanY * effectiveScaleRatio +
                                    (prevFocalY - centerY) * (1f - effectiveScaleRatio) + focalDeltaY

                            val (maxPanX, maxPanY) = calculatePanBounds(
                                viewWidth, viewHeight, imageWidth, imageHeight, isFitMode, targetZoom
                            )

                            if (targetZoom <= 1.001f) {
                                targetPanX = 0f; targetPanY = 0f
                            } else {
                                targetPanX = targetPanX.coerceIn(-maxPanX, maxPanX)
                                targetPanY = targetPanY.coerceIn(-maxPanY, maxPanY)
                            }

                            onTransformUpdate(targetZoom, targetPanX, targetPanY)

                        } else {
                            // Two-finger pan of the Android view
                            var targetPanX = currentPanX + focalDeltaX
                            var targetPanY = currentPanY + focalDeltaY

                            val (maxPanX, maxPanY) = calculatePanBounds(
                                viewWidth, viewHeight, imageWidth, imageHeight, isFitMode, currentZoom
                            )

                            if (currentZoom <= 1.001f) {
                                // ── Two-finger scroll → send Windows scroll wheel ──
                                scrollAccumY += focalDeltaY
                                while (scrollAccumY >= scrollTickPx) {
                                    // Fingers moved down → scroll up on Windows
                                    sendInput(InputEventProtocol.serializeMouseScroll(0, -scrollWheelAmount))
                                    scrollAccumY -= scrollTickPx
                                }
                                while (scrollAccumY <= -scrollTickPx) {
                                    // Fingers moved up → scroll down on Windows
                                    sendInput(InputEventProtocol.serializeMouseScroll(0, scrollWheelAmount))
                                    scrollAccumY += scrollTickPx
                                }
                                // No view transform needed at 1× — view stays put
                            } else {
                                // Pan the zoomed view
                                scrollAccumY = 0f
                                targetPanX = targetPanX.coerceIn(-maxPanX, maxPanX)
                                targetPanY = targetPanY.coerceIn(-maxPanY, maxPanY)
                                onTransformUpdate(currentZoom, targetPanX, targetPanY)
                            }
                        }
                    }

                    prevFingerDistance = currDistance
                    prevFocalX         = currFocalX
                    prevFocalY         = currFocalY
                }
                return true
            }

            // ── A non-primary finger lifts ─────────────────────────────────────
            MotionEvent.ACTION_POINTER_UP -> {
                prevFingerDistance = 0f
                scrollAccumY       = 0f
                return true
            }

            // ── Last finger lifts ──────────────────────────────────────────────
            MotionEvent.ACTION_UP -> {
                cancelLongPress()
                val touchDuration = System.currentTimeMillis() - initialTouchTime

                // A valid tap: single touch, no movement, within duration threshold, no long-press fired
                if (!isMultiTouch && !hasMovedBeyondSlop &&
                    touchDuration < maxTapDurationMs && !longPressFired
                ) {
                    val (normX, normY) = mapScreenToWindows(
                        screenX     = event.x,
                        screenY     = event.y,
                        viewWidth   = viewWidth,
                        viewHeight  = viewHeight,
                        imageWidth  = imageWidth,
                        imageHeight = imageHeight,
                        isFitMode   = isFitMode,
                        zoom        = currentZoom,
                        panX        = currentPanX,
                        panY        = currentPanY
                    )

                    val now = System.currentTimeMillis()
                    val timeSinceLastTap = now - lastTapTime
                    val distFromLastTap  = hypot(
                        (event.x - lastTapX).toDouble(),
                        (event.y - lastTapY).toDouble()
                    ).toFloat()

                    if (timeSinceLastTap <= doubleTapWindowMs && distFromLastTap <= doubleTapSlopPx) {
                        // ── Double-tap → Windows double-click ──────────────────
                        // Reset last-tap so a third tap won't triple-fire
                        lastTapTime = 0L
                        triggerHaptic(longPress = false)
                        sendInput(InputEventProtocol.serializeMouseMove(normX, normY))
                        sendInput(InputEventProtocol.serializeMouseButton("left", "double_click"))
                    } else {
                        // ── Single tap → Windows left-click ───────────────────
                        lastTapTime = now
                        lastTapX    = event.x
                        lastTapY    = event.y
                        triggerHaptic(longPress = false)
                        sendInput(InputEventProtocol.serializeMouseMove(normX, normY))
                        sendInput(InputEventProtocol.serializeMouseButton("left", "click"))
                    }
                }

                // Reset state
                isMultiTouch       = false
                hasMovedBeyondSlop = false
                longPressFired     = false
                prevFingerDistance = 0f
                scrollAccumY       = 0f
                return true
            }

            // ── Gesture cancelled (e.g. system interrupt) ──────────────────────
            MotionEvent.ACTION_CANCEL -> {
                cancelLongPress()
                isMultiTouch       = false
                hasMovedBeyondSlop = false
                longPressFired     = false
                prevFingerDistance = 0f
                scrollAccumY       = 0f
                return true
            }
        }
        return false
    }

    // ── Helpers ────────────────────────────────────────────────────────────────

    private fun cancelLongPress() {
        longPressRunnable?.let { mainHandler.removeCallbacks(it) }
        longPressRunnable = null
    }

    private fun triggerHaptic(longPress: Boolean) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                val duration = if (longPress) 60L else 35L
                vibrator?.vibrate(VibrationEffect.createOneShot(duration, VibrationEffect.DEFAULT_AMPLITUDE))
            } else {
                @Suppress("DEPRECATION")
                vibrator?.vibrate(if (longPress) 60L else 35L)
            }
        } catch (_: Exception) {}
    }
}
