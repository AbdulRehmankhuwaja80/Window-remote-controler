package com.remodesk.client.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.remodesk.client.ui.theme.CharcoalSurface
import com.remodesk.client.ui.theme.CharcoalSurfaceVariant
import com.remodesk.client.ui.theme.ElectricBluePrimary
import com.remodesk.client.webrtc.InputEventProtocol

@Composable
fun OnScreenKeyboardBar(
    modifier: Modifier = Modifier,
    sendInput: (String) -> Unit
) {
    var ctrlActive by remember { mutableStateOf(false) }
    var altActive by remember { mutableStateOf(false) }
    var shiftActive by remember { mutableStateOf(false) }
    var winActive by remember { mutableStateOf(false) }

    var textInput by remember { mutableStateOf("") }

    Column(
        modifier = modifier
            .fillMaxWidth()
            .background(CharcoalSurface)
            .padding(8.dp)
    ) {
        // Quick Text Sender
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedTextField(
                value = textInput,
                onValueChange = { textInput = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("Type text to send to Windows...") },
                singleLine = true,
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = ElectricBluePrimary,
                    unfocusedBorderColor = CharcoalSurfaceVariant
                )
            )

            Button(
                onClick = {
                    if (textInput.isNotEmpty()) {
                        sendInput(InputEventProtocol.serializeTextInput(textInput))
                        textInput = ""
                    }
                },
                shape = RoundedCornerShape(8.dp),
                colors = ButtonDefaults.buttonColors(containerColor = ElectricBluePrimary)
            ) {
                Text("Send")
            }
        }

        Spacer(modifier = Modifier.height(8.dp))

        // Horizontal Modifier & Special Keys Bar
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            // Ctrl
            FilterChip(
                selected = ctrlActive,
                onClick = {
                    ctrlActive = !ctrlActive
                    val action = if (ctrlActive) "down" else "up"
                    sendInput(InputEventProtocol.serializeKeyEvent(17, action))
                },
                label = { Text("Ctrl", fontSize = 12.sp) }
            )

            // Alt
            FilterChip(
                selected = altActive,
                onClick = {
                    altActive = !altActive
                    val action = if (altActive) "down" else "up"
                    sendInput(InputEventProtocol.serializeKeyEvent(18, action))
                },
                label = { Text("Alt", fontSize = 12.sp) }
            )

            // Shift
            FilterChip(
                selected = shiftActive,
                onClick = {
                    shiftActive = !shiftActive
                    val action = if (shiftActive) "down" else "up"
                    sendInput(InputEventProtocol.serializeKeyEvent(16, action))
                },
                label = { Text("Shift", fontSize = 12.sp) }
            )

            // Win Key
            FilterChip(
                selected = winActive,
                onClick = {
                    winActive = !winActive
                    val action = if (winActive) "down" else "up"
                    sendInput(InputEventProtocol.serializeKeyEvent(91, action, extended = true))
                },
                label = { Text("Win", fontSize = 12.sp) }
            )

            // Esc
            KeyButton(text = "Esc") {
                sendInput(InputEventProtocol.serializeKeyEvent(27, "down"))
                sendInput(InputEventProtocol.serializeKeyEvent(27, "up"))
            }

            // Tab
            KeyButton(text = "Tab") {
                sendInput(InputEventProtocol.serializeKeyEvent(9, "down"))
                sendInput(InputEventProtocol.serializeKeyEvent(9, "up"))
            }

            // Enter
            KeyButton(text = "Enter") {
                sendInput(InputEventProtocol.serializeKeyEvent(13, "down"))
                sendInput(InputEventProtocol.serializeKeyEvent(13, "up"))
            }

            // Backspace
            KeyButton(text = "⌫") {
                sendInput(InputEventProtocol.serializeKeyEvent(8, "down"))
                sendInput(InputEventProtocol.serializeKeyEvent(8, "up"))
            }

            // Shortcuts
            KeyButton(text = "Win+D") {
                sendInput(InputEventProtocol.serializeKeyEvent(91, "down", true))
                sendInput(InputEventProtocol.serializeKeyEvent(68, "down"))
                sendInput(InputEventProtocol.serializeKeyEvent(68, "up"))
                sendInput(InputEventProtocol.serializeKeyEvent(91, "up", true))
            }

            KeyButton(text = "Alt+Tab") {
                sendInput(InputEventProtocol.serializeKeyEvent(18, "down"))
                sendInput(InputEventProtocol.serializeKeyEvent(9, "down"))
                sendInput(InputEventProtocol.serializeKeyEvent(9, "up"))
                sendInput(InputEventProtocol.serializeKeyEvent(18, "up"))
            }

            KeyButton(text = "Copy (Ctrl+C)") {
                sendInput(InputEventProtocol.serializeKeyEvent(17, "down"))
                sendInput(InputEventProtocol.serializeKeyEvent(67, "down"))
                sendInput(InputEventProtocol.serializeKeyEvent(67, "up"))
                sendInput(InputEventProtocol.serializeKeyEvent(17, "up"))
            }

            KeyButton(text = "Paste (Ctrl+V)") {
                sendInput(InputEventProtocol.serializeKeyEvent(17, "down"))
                sendInput(InputEventProtocol.serializeKeyEvent(86, "down"))
                sendInput(InputEventProtocol.serializeKeyEvent(86, "up"))
                sendInput(InputEventProtocol.serializeKeyEvent(17, "up"))
            }
        }
    }
}

@Composable
private fun KeyButton(text: String, onClick: () -> Unit) {
    FilledTonalButton(
        onClick = onClick,
        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp),
        shape = RoundedCornerShape(8.dp)
    ) {
        Text(text, fontSize = 12.sp)
    }
}
