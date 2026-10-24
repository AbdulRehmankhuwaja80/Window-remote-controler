package com.remodesk.client.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.remodesk.client.data.Device
import com.remodesk.client.data.TokenManager
import com.remodesk.client.network.ApiService
import com.remodesk.client.ui.theme.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    tokenManager: TokenManager,
    onConnectDevice: (Device) -> Unit,
    onNavigateToFileManager: (Device) -> Unit,
    onNavigateToSettings: () -> Unit,
    onLogout: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var devices by remember { mutableStateOf<List<Device>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var deviceToRename by remember { mutableStateOf<Device?>(null) }
    var newDeviceName by remember { mutableStateOf("") }
    var showPairDialog by remember { mutableStateOf(false) }
    var partnerIdInput by remember { mutableStateOf("") }
    var pinInput by remember { mutableStateOf("") }
    var isPairing by remember { mutableStateOf(false) }

    fun refreshDevices() {
        isLoading = true
        coroutineScope.launch {
            try {
                val api = ApiService.create(tokenManager.serverUrl, tokenManager)
                devices = api.listDevices()
            } catch (e: Exception) {
                Toast.makeText(context, "Could not load devices: ${e.message}", Toast.LENGTH_SHORT).show()
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(Unit) {
        refreshDevices()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("RemoDesk", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        Text(
                            text = tokenManager.userEmail ?: "Registered Laptops",
                            color = TextSecondary,
                            fontSize = 12.sp
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { refreshDevices() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = TextPrimary)
                    }
                    IconButton(onClick = onNavigateToSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "Settings", tint = TextPrimary)
                    }
                    IconButton(onClick = onLogout) {
                        Icon(Icons.Default.ExitToApp, contentDescription = "Sign Out", tint = StatusError)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = CharcoalSurface)
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showPairDialog = true },
                containerColor = ElectricBluePrimary,
                contentColor = Color.White
            ) {
                Icon(Icons.Default.Add, contentDescription = "Link Partner Laptop")
            }
        },
        containerColor = DarkNavyBackground
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            if (isLoading && devices.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = ElectricBluePrimary)
                }
            } else if (devices.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(32.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            imageVector = Icons.Default.LaptopWindows,
                            contentDescription = null,
                            tint = TextSecondary,
                            modifier = Modifier.size(64.dp)
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Text(
                            text = "No Laptops Linked Yet",
                            style = MaterialTheme.typography.titleMedium,
                            color = TextPrimary
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "Start RemoDesk on your laptop and enter the 6-digit PIN shown on your screen to connect.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = TextSecondary,
                            textAlign = androidx.compose.ui.text.style.TextAlign.Center
                        )
                        Spacer(modifier = Modifier.height(24.dp))
                        Button(
                            onClick = { showPairDialog = true },
                            colors = ButtonDefaults.buttonColors(containerColor = ElectricBluePrimary),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth(0.8f)
                        ) {
                            Icon(Icons.Default.Add, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Link Laptop (Enter PIN)")
                        }
                        Spacer(modifier = Modifier.height(12.dp))
                        OutlinedButton(
                            onClick = { refreshDevices() },
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth(0.8f)
                        ) {
                            Icon(Icons.Default.Refresh, contentDescription = null)
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Refresh List")
                        }
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    items(devices) { device ->
                        DeviceCard(
                            device = device,
                            onConnect = { onConnectDevice(device) },
                            onFiles = { onNavigateToFileManager(device) },
                            onRename = {
                                deviceToRename = device
                                newDeviceName = device.deviceName
                            },
                            onDelete = {
                                coroutineScope.launch {
                                    try {
                                        val api = ApiService.create(tokenManager.serverUrl, tokenManager)
                                        api.deleteDevice(device.id)
                                        Toast.makeText(context, "Device removed.", Toast.LENGTH_SHORT).show()
                                        refreshDevices()
                                    } catch (e: Exception) {
                                        Toast.makeText(context, "Failed to delete: ${e.message}", Toast.LENGTH_SHORT).show()
                                    }
                                }
                            }
                        )
                    }
                }
            }
        }
    }

    // Rename Dialog
    deviceToRename?.let { dev ->
        AlertDialog(
            onDismissRequest = { deviceToRename = null },
            title = { Text("Rename Device") },
            text = {
                OutlinedTextField(
                    value = newDeviceName,
                    onValueChange = { newDeviceName = it },
                    singleLine = true,
                    label = { Text("Device Name") }
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    coroutineScope.launch {
                        try {
                            val api = ApiService.create(tokenManager.serverUrl, tokenManager)
                            api.updateDevice(dev.id, mapOf("device_name" to newDeviceName.trim()))
                            deviceToRename = null
                            refreshDevices()
                        } catch (e: Exception) {
                            Toast.makeText(context, "Update failed: ${e.message}", Toast.LENGTH_SHORT).show()
                        }
                    }
                }) {
                    Text("Save")
                }
            },
            dismissButton = {
                TextButton(onClick = { deviceToRename = null }) {
                    Text("Cancel")
                }
            }
        )
    }

    // TeamViewer-style Pairing Dialog
    if (showPairDialog) {
        AlertDialog(
            onDismissRequest = { if (!isPairing) showPairDialog = false },
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Default.LaptopWindows, contentDescription = null, tint = ElectricBluePrimary)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Link Partner Laptop", fontWeight = FontWeight.Bold, color = TextPrimary)
                }
            },
            text = {
                Column {
                    Text(
                        "Enter the Partner ID and 6-digit PIN shown on your laptop screen (like TeamViewer) to save it as your go-to device.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = TextSecondary
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    OutlinedTextField(
                        value = partnerIdInput,
                        onValueChange = { partnerIdInput = it.take(40) },
                        label = { Text("Partner ID (e.g. Laptop Name)") },
                        placeholder = { Text("e.g. LAPTOP-4A9AUPQS") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = ElectricBluePrimary,
                            unfocusedBorderColor = CharcoalSurfaceVariant
                        )
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    OutlinedTextField(
                        value = pinInput,
                        onValueChange = { pinInput = it.take(10) },
                        label = { Text("One-Time PIN (6 digits)") },
                        placeholder = { Text("e.g. 467008") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedBorderColor = ElectricBluePrimary,
                            unfocusedBorderColor = CharcoalSurfaceVariant
                        )
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val pid = partnerIdInput.trim()
                        val pin = pinInput.trim()
                        if (pin.isEmpty()) return@Button
                        isPairing = true
                        coroutineScope.launch {
                            try {
                                val api = ApiService.create(tokenManager.serverUrl, tokenManager)
                                val body = mutableMapOf("pin" to pin)
                                if (pid.isNotEmpty()) {
                                    body["partner_id"] = pid
                                }
                                val dev = api.pairDevice(pairingCode = pin, body = body)
                                Toast.makeText(context, "Linked ${dev.deviceName} successfully!", Toast.LENGTH_SHORT).show()
                                showPairDialog = false
                                partnerIdInput = ""
                                pinInput = ""
                                refreshDevices()
                            } catch (e: Exception) {
                                Toast.makeText(context, "Pairing failed: ${e.message}", Toast.LENGTH_LONG).show()
                            } finally {
                                isPairing = false
                            }
                        }
                    },
                    enabled = !isPairing && pinInput.isNotBlank(),
                    colors = ButtonDefaults.buttonColors(containerColor = ElectricBluePrimary)
                ) {
                    Text(if (isPairing) "Linking..." else "Link Laptop")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = { showPairDialog = false },
                    enabled = !isPairing
                ) {
                    Text("Cancel", color = TextSecondary)
                }
            },
            containerColor = CharcoalSurface
        )
    }
}

@Composable
fun DeviceCard(
    device: Device,
    onConnect: () -> Unit,
    onFiles: () -> Unit,
    onRename: () -> Unit,
    onDelete: () -> Unit
) {
    val isOnline = device.status.equals("ONLINE", ignoreCase = true)
    val statusColor = when (device.status.uppercase()) {
        "ONLINE" -> StatusOnline
        "IN_SESSION" -> CyanSecondary
        "PAUSED" -> StatusWarning
        else -> TextSecondary
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = CharcoalSurface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Header Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(12.dp)
                            .clip(CircleShape)
                            .background(statusColor)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = device.deviceName,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                }

                Row {
                    IconButton(onClick = onRename, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.Default.Edit, contentDescription = "Rename", tint = TextSecondary, modifier = Modifier.size(18.dp))
                    }
                    IconButton(onClick = onDelete, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.Default.Delete, contentDescription = "Delete", tint = StatusError, modifier = Modifier.size(18.dp))
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Sub-info
            Text(
                text = "OS: ${device.osInfo}  •  Status: ${device.status}",
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary
            )
            Text(
                text = "Remote Access: ${if (device.isRemoteEnabled) "Enabled" else "Disabled"}",
                style = MaterialTheme.typography.bodySmall,
                color = if (device.isRemoteEnabled) StatusOnline else StatusWarning
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Action Buttons
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Button(
                    onClick = onConnect,
                    enabled = isOnline && device.isRemoteEnabled,
                    modifier = Modifier
                        .weight(1f)
                        .height(46.dp),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = ElectricBluePrimary,
                        disabledContainerColor = CharcoalSurfaceVariant
                    )
                ) {
                    Icon(Icons.Default.Cast, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (isOnline) "Connect" else "Offline",
                        fontWeight = FontWeight.SemiBold
                    )
                }

                OutlinedButton(
                    onClick = onFiles,
                    enabled = isOnline,
                    modifier = Modifier.height(46.dp),
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = CyanSecondary)
                ) {
                    Icon(Icons.Default.Folder, contentDescription = "Files", modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("Files")
                }
            }
        }
    }
}
