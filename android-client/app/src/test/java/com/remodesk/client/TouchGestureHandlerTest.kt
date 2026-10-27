package com.remodesk.client

import com.remodesk.client.ui.screens.TouchGestureHandler
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TouchGestureHandlerTest {

    private val delta = 0.001f

    @Test
    fun testZoomConstants() {
        assertEquals(1.0f, TouchGestureHandler.MIN_ZOOM, delta)
        assertEquals(4.0f, TouchGestureHandler.MAX_ZOOM, delta)
    }

    @Test
    fun testMapScreenToWindows_centered_returnsCenter() {
        val (normX, normY) = TouchGestureHandler.mapScreenToWindows(
            screenX = 540f,
            screenY = 960f,
            viewWidth = 1080f,
            viewHeight = 1920f,
            imageWidth = 1920f,
            imageHeight = 1080f,
            isFitMode = true,
            zoom = 1.0f,
            panX = 0f,
            panY = 0f
        )

        assertEquals(0.5f, normX, delta)
        assertEquals(0.5f, normY, delta)
    }

    @Test
    fun testMapScreenToWindows_fitMode_square() {
        val (leftX, topY) = TouchGestureHandler.mapScreenToWindows(
            screenX = 0f,
            screenY = 0f,
            viewWidth = 1000f,
            viewHeight = 1000f,
            imageWidth = 1000f,
            imageHeight = 1000f,
            isFitMode = true,
            zoom = 1.0f,
            panX = 0f,
            panY = 0f
        )
        assertEquals(0.0f, leftX, delta)
        assertEquals(0.0f, topY, delta)

        val (rightX, bottomY) = TouchGestureHandler.mapScreenToWindows(
            screenX = 1000f,
            screenY = 1000f,
            viewWidth = 1000f,
            viewHeight = 1000f,
            imageWidth = 1000f,
            imageHeight = 1000f,
            isFitMode = true,
            zoom = 1.0f,
            panX = 0f,
            panY = 0f
        )
        assertEquals(1.0f, rightX, delta)
        assertEquals(1.0f, bottomY, delta)
    }

    @Test
    fun testMapScreenToWindows_withZoom() {
        // At 2x centered zoom, the center still maps to 0.5, 0.5
        val (centerX, centerY) = TouchGestureHandler.mapScreenToWindows(
            screenX = 500f,
            screenY = 500f,
            viewWidth = 1000f,
            viewHeight = 1000f,
            imageWidth = 1000f,
            imageHeight = 1000f,
            isFitMode = true,
            zoom = 2.0f,
            panX = 0f,
            panY = 0f
        )
        assertEquals(0.5f, centerX, delta)
        assertEquals(0.5f, centerY, delta)

        // Screen (0, 0) maps to 0.25, 0.25 when zoomed 2x without pan
        val (screenZeroX, screenZeroY) = TouchGestureHandler.mapScreenToWindows(
            screenX = 0f,
            screenY = 0f,
            viewWidth = 1000f,
            viewHeight = 1000f,
            imageWidth = 1000f,
            imageHeight = 1000f,
            isFitMode = true,
            zoom = 2.0f,
            panX = 0f,
            panY = 0f
        )
        assertEquals(0.25f, screenZeroX, delta)
        assertEquals(0.25f, screenZeroY, delta)

        // Screen (1000, 1000) maps to 0.75, 0.75 when zoomed 2x without pan
        val (screenMaxX, screenMaxY) = TouchGestureHandler.mapScreenToWindows(
            screenX = 1000f,
            screenY = 1000f,
            viewWidth = 1000f,
            viewHeight = 1000f,
            imageWidth = 1000f,
            imageHeight = 1000f,
            isFitMode = true,
            zoom = 2.0f,
            panX = 0f,
            panY = 0f
        )
        assertEquals(0.75f, screenMaxX, delta)
        assertEquals(0.75f, screenMaxY, delta)
    }

    @Test
    fun testMapScreenToWindows_withZoomAndPan() {
        // At 2x zoom panned right by 500px, screenX = 0 should align with left edge (normX = 0.0)
        val (pannedLeftX, pannedY) = TouchGestureHandler.mapScreenToWindows(
            screenX = 0f,
            screenY = 500f,
            viewWidth = 1000f,
            viewHeight = 1000f,
            imageWidth = 1000f,
            imageHeight = 1000f,
            isFitMode = true,
            zoom = 2.0f,
            panX = 500f,
            panY = 0f
        )
        assertEquals(0.0f, pannedLeftX, delta)
        assertEquals(0.5f, pannedY, delta)
    }

    @Test
    fun testCalculatePanBounds_atOneZoom_returnsZero() {
        val (panX, panY) = TouchGestureHandler.calculatePanBounds(
            viewWidth = 1000f,
            viewHeight = 1000f,
            imageWidth = 1000f,
            imageHeight = 1000f,
            isFitMode = true,
            zoom = 1.0f
        )
        assertEquals(0.0f, panX, delta)
        assertEquals(0.0f, panY, delta)
    }

    @Test
    fun testCalculatePanBounds_atTwoZoom_returnsCorrectBounds() {
        val (panX, panY) = TouchGestureHandler.calculatePanBounds(
            viewWidth = 1000f,
            viewHeight = 1000f,
            imageWidth = 1000f,
            imageHeight = 1000f,
            isFitMode = true,
            zoom = 2.0f
        )
        // content = 2000, view = 1000 -> maxPan = (2000 - 1000) / 2 = 500
        assertEquals(500.0f, panX, delta)
        assertEquals(500.0f, panY, delta)
    }

    @Test
    fun testCalculatePanBounds_letterboxDimension_panClampedToZero() {
        // Portrait phone: view 1080x2400, 16:9 remote desktop: 1920x1080
        // renderedW = 1080, renderedH = 607.5
        // At 2.0x zoom: contentW = 2160 (> 1080), contentH = 1215 (< 2400)
        val (panX, panY) = TouchGestureHandler.calculatePanBounds(
            viewWidth = 1080f,
            viewHeight = 2400f,
            imageWidth = 1920f,
            imageHeight = 1080f,
            isFitMode = true,
            zoom = 2.0f
        )
        assertEquals(540.0f, panX, delta)
        assertEquals(0.0f, panY, delta)
    }
}
