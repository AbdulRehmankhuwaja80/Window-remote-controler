package com.remodesk.client.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
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
import com.remodesk.client.data.Device
import com.remodesk.client.data.FileItem
import com.remodesk.client.ui.theme.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FileTransferScreen(
    device: Device,
    onNavigateBack: () -> Unit
) {
    val context = LocalContext.current
    var currentPath by remember { mutableStateOf("C:\\Users\\LaptopUser") }
    var filesList by remember {
        mutableStateOf(
            listOf(
                FileItem("Documents", "$currentPath\\Documents", isDirectory = true, size = 0, modifiedAt = "2026-10-14"),
                FileItem("Downloads", "$currentPath\\Downloads", isDirectory = true, size = 0, modifiedAt = "2026-10-15"),
                FileItem("Desktop", "$currentPath\\Desktop", isDirectory = true, size = 0, modifiedAt = "2026-10-15"),
                FileItem("Quarterly_Report_2026.pdf", "$currentPath\\Quarterly_Report_2026.pdf", isDirectory = false, size = 2450000, modifiedAt = "2026-10-12"),
                FileItem("Project_Plan.docx", "$currentPath\\Project_Plan.docx", isDirectory = false, size = 520000, modifiedAt = "2026-10-11")
            )
        )
    }

    var isTransferring by remember { mutableStateOf(false) }
    var transferProgress by remember { mutableStateOf(0.45f) }
    var transferFilename by remember { mutableStateOf("") }
    var fileToDelete by remember { mutableStateOf<FileItem?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("Remote File Explorer", color = TextPrimary, fontSize = 18.sp, fontWeight = FontWeight.Bold)
                        Text(device.deviceName, color = TextSecondary, fontSize = 12.sp)
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = TextPrimary)
                    }
                },
                actions = {
                    IconButton(onClick = {
                        // Mock Upload Action
                        transferFilename = "Mobile_Upload_${System.currentTimeMillis()}.png"
                        isTransferring = true
                        Toast.makeText(context, "Uploading file to laptop...", Toast.LENGTH_SHORT).show()
                    }) {
                        Icon(Icons.Default.Upload, contentDescription = "Upload", tint = CyanSecondary)
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
        ) {
            // Path Navigation Header
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = CharcoalSurfaceVariant
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Default.FolderOpen, contentDescription = null, tint = CyanSecondary, modifier = Modifier.size(20.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = currentPath,
                        style = MaterialTheme.typography.bodySmall,
                        color = TextPrimary,
                        maxLines = 1
                    )
                }
            }

            // Progress Banner
            if (isTransferring) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    colors = CardDefaults.cardColors(containerColor = CharcoalSurface),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(12.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(transferFilename, style = MaterialTheme.typography.bodyMedium, color = TextPrimary)
                            Text("${(transferProgress * 100).toInt()}%", style = MaterialTheme.typography.bodyMedium, color = CyanSecondary)
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                        LinearProgressIndicator(
                            progress = { transferProgress },
                            modifier = Modifier.fillMaxWidth(),
                            color = CyanSecondary,
                            trackColor = CharcoalSurfaceVariant
                        )
                    }
                }
            }

            // File Entries List
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(filesList) { item ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clickable {
                                if (item.isDirectory) {
                                    currentPath = item.path
                                } else {
                                    transferFilename = item.name
                                    isTransferring = true
                                    Toast.makeText(context, "Downloading ${item.name}...", Toast.LENGTH_SHORT).show()
                                }
                            },
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = CharcoalSurface)
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = if (item.isDirectory) Icons.Default.Folder else Icons.Default.InsertDriveFile,
                                    contentDescription = null,
                                    tint = if (item.isDirectory) CyanSecondary else TextSecondary,
                                    modifier = Modifier.size(28.dp)
                                )
                                Spacer(modifier = Modifier.width(12.dp))
                                Column {
                                    Text(item.name, color = TextPrimary, fontWeight = FontWeight.SemiBold, fontSize = 14.sp)
                                    val sizeStr = if (item.isDirectory) "Folder" else "${item.size / 1024} KB"
                                    Text("$sizeStr  •  ${item.modifiedAt}", color = TextSecondary, fontSize = 11.sp)
                                }
                            }

                            Row {
                                if (!item.isDirectory) {
                                    IconButton(onClick = {
                                        transferFilename = item.name
                                        isTransferring = true
                                    }) {
                                        Icon(Icons.Default.Download, contentDescription = "Download", tint = ElectricBluePrimary)
                                    }
                                }
                                IconButton(onClick = { fileToDelete = item }) {
                                    Icon(Icons.Default.Delete, contentDescription = "Delete", tint = StatusError)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Confirm Delete Dialog
    fileToDelete?.let { item ->
        AlertDialog(
            onDismissRequest = { fileToDelete = null },
            title = { Text("Delete Confirmation") },
            text = { Text("Are you sure you want to delete '${item.name}' from your laptop? This cannot be undone.") },
            confirmButton = {
                TextButton(
                    onClick = {
                        filesList = filesList.filter { it.path != item.path }
                        fileToDelete = null
                        Toast.makeText(context, "Deleted from laptop.", Toast.LENGTH_SHORT).show()
                    },
                    colors = ButtonDefaults.textButtonColors(contentColor = StatusError)
                ) {
                    Text("Delete")
                }
            },
            dismissButton = {
                TextButton(onClick = { fileToDelete = null }) {
                    Text("Cancel")
                }
            }
        )
    }
}
