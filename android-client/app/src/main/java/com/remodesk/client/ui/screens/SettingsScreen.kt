package com.remodesk.client.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.remodesk.client.data.TokenManager
import com.remodesk.client.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    tokenManager: TokenManager,
    onNavigateBack: () -> Unit
) {
    val context = LocalContext.current
    var sensitivity by remember { mutableStateOf(tokenManager.touchpadSensitivity) }
    var biometricEnabled by remember { mutableStateOf(tokenManager.isBiometricEnabled) }
    var serverUrl by remember { mutableStateOf(tokenManager.serverUrl) }
    var selectedQuality by remember { mutableStateOf("Balanced (1080p / 30fps)") }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings & Preferences", color = TextPrimary, fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = TextPrimary)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = CharcoalSurface)
            )
        },
        containerColor = DarkNavyBackground
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            // Touchpad Sensitivity Section
            Card(
                colors = CardDefaults.cardColors(containerColor = CharcoalSurface),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Touchpad Sensitivity", style = MaterialTheme.typography.titleMedium, color = TextPrimary)
                    Text("Adjust virtual trackpad speed and ballistics", style = MaterialTheme.typography.bodySmall, color = TextSecondary)
                    Spacer(modifier = Modifier.height(12.dp))
                    Slider(
                        value = sensitivity,
                        onValueChange = {
                            sensitivity = it
                            tokenManager.touchpadSensitivity = it
                        },
                        valueRange = 0.5f..3.0f,
                        colors = SliderDefaults.colors(thumbColor = ElectricBluePrimary, activeTrackColor = ElectricBluePrimary)
                    )
                    Text("Current speed: ${String.format("%.1f", sensitivity)}x", color = CyanSecondary, fontSize = 12.sp)
                }
            }

            // Streaming Quality Section
            Card(
                colors = CardDefaults.cardColors(containerColor = CharcoalSurface),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Video Streaming Quality", style = MaterialTheme.typography.titleMedium, color = TextPrimary)
                    Text("Adaptive streaming prioritizes low latency over mobile data", style = MaterialTheme.typography.bodySmall, color = TextSecondary)
                    Spacer(modifier = Modifier.height(12.dp))
                    listOf("Low Latency (720p / 60fps)", "Balanced (1080p / 30fps)", "High Definition (1080p / 60fps)").forEach { opt ->
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            RadioButton(
                                selected = (selectedQuality == opt),
                                onClick = { selectedQuality = opt },
                                colors = RadioButtonDefaults.colors(selectedColor = ElectricBluePrimary)
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(opt, color = TextPrimary, fontSize = 14.sp)
                        }
                    }
                }
            }

            // Security & Privacy Disclosure Section
            Card(
                colors = CardDefaults.cardColors(containerColor = CharcoalSurface),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Security & Privacy", style = MaterialTheme.typography.titleMedium, color = TextPrimary)
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text("Biometric Authentication", color = TextPrimary, fontSize = 14.sp)
                            Text("Unlock remote sessions with fingerprint or face recognition", color = TextSecondary, fontSize = 12.sp)
                        }
                        Switch(
                            checked = biometricEnabled,
                            onCheckedChange = {
                                biometricEnabled = it
                                tokenManager.isBiometricEnabled = it
                            },
                            colors = SwitchDefaults.colors(checkedThumbColor = ElectricBluePrimary)
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    Surface(
                        color = CharcoalSurfaceVariant,
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(Icons.Default.Security, contentDescription = null, tint = StatusOnline, modifier = Modifier.size(24.dp))
                            Spacer(modifier = Modifier.width(12.dp))
                            Text(
                                "Zero-Trust Encryption: All media and input streams are encrypted end-to-end via DTLS-SRTP and SCTP. Microphones and webcams are never silently activated.",
                                color = TextSecondary,
                                fontSize = 11.sp
                            )
                        }
                    }
                }
            }

            // Gateway Configuration Section
            Card(
                colors = CardDefaults.cardColors(containerColor = CharcoalSurface),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Cloud Gateway URL", style = MaterialTheme.typography.titleMedium, color = TextPrimary)
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = serverUrl,
                        onValueChange = { serverUrl = it },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = CyanSecondary,
                            unfocusedBorderColor = CharcoalSurfaceVariant
                        )
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    Button(
                        onClick = {
                            tokenManager.serverUrl = serverUrl.trim()
                            Toast.makeText(context, "Gateway URL saved.", Toast.LENGTH_SHORT).show()
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = ElectricBluePrimary)
                    ) {
                        Text("Save Gateway URL")
                    }
                }
            }
        }
    }
}
