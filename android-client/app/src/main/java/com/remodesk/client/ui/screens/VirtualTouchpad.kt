package com.remodesk.client.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.remodesk.client.ui.theme.CharcoalSurface
import com.remodesk.client.ui.theme.CharcoalSurfaceVariant
import com.remodesk.client.ui.theme.ElectricBluePrimary
import com.remodesk.client.webrtc.InputEventProtocol

@Composable
fun VirtualTouchpad(
    modifier: Modifier = Modifier,
    sensitivity: Float = 1.2f,
    sendInput: (String) -> Unit
) {
    Column(
        modifier = modifier
            .fillMaxWidth()
            .height(240.dp)
            .background(CharcoalSurface, shape = RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp))
            .padding(12.dp)
    ) {
        // Touchpad Area
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .weight(1f)
                .background(CharcoalSurfaceVariant, shape = RoundedCornerShape(12.dp))
                .pointerInput(sensitivity) {
                    detectDragGestures { change, dragAmount ->
                        change.consume()
                        val dx = (dragAmount.x * sensitivity).toInt()
                        val dy = (dragAmount.y * sensitivity).toInt()
                        if (dx != 0 || dy != 0) {
                            sendInput(InputEventProtocol.serializeMouseDelta(dx, dy))
                        }
                    }
                },
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "Touchpad Surface (Drag to move cursor)",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        Spacer(modifier = Modifier.height(10.dp))

        // Physical-Style Mouse Buttons
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .height(55.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Button(
                onClick = {
                    sendInput(InputEventProtocol.serializeMouseButton("left", "click"))
                },
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight(),
                shape = RoundedCornerShape(8.dp),
                colors = ButtonDefaults.buttonColors(containerColor = ElectricBluePrimary)
            ) {
                Text("Left Click")
            }

            Button(
                onClick = {
                    sendInput(InputEventProtocol.serializeMouseButton("right", "click"))
                },
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight(),
                shape = RoundedCornerShape(8.dp),
                colors = ButtonDefaults.buttonColors(containerColor = CharcoalSurfaceVariant)
            ) {
                Text("Right Click")
            }
        }
    }
}
