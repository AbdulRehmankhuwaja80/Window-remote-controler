package com.remodesk.client.ui.screens

import android.net.Uri
import android.os.Environment
import android.provider.OpenableColumns
import android.util.Base64
import android.widget.Toast
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import com.remodesk.client.data.TokenManager
import com.remodesk.client.network.SignalingClient
import com.remodesk.client.ui.theme.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream

data class PendingUpload(
    val uri: Uri,
    val filename: String,
    val totalSize: Long,
    val targetDirectory: String,
    var currentOffset: Long = 0L
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FileTransferScreen(
    device: Device,
    tokenManager: TokenManager,
    signalingClient: SignalingClient? = null,
    onNavigateBack: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var currentPath by remember { mutableStateOf("") }
    var filesList by remember { mutableStateOf<List<FileItem>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }

    var isTransferring by remember { mutableStateOf(false) }
    var transferProgress by remember { mutableFloatStateOf(0f) }
    var transferFilename by remember { mutableStateOf("") }
    var transferStatusText by remember { mutableStateOf("") }

    var fileToDelete by remember { mutableStateOf<FileItem?>(null) }
    var pendingUpload by remember { mutableStateOf<PendingUpload?>(null) }
    var showOverwriteDialog by remember { mutableStateOf(false) }

    // Active client instance (reused or created)
    var activeClient by remember { mutableStateOf<SignalingClient?>(signalingClient) }
    var isLocalClient by remember { mutableStateOf(false) }

    // State for ongoing download
    var currentDownloadFile by remember { mutableStateOf<File?>(null) }
    var currentDownloadOutputStream by remember { mutableStateOf<FileOutputStream?>(null) }
    var currentDownloadTotalSize by remember { mutableLongStateOf(0L) }
    var currentDownloadReceivedSize by remember { mutableLongStateOf(0L) }

    val chunkSize = 65536 // 64 KB chunks

    fun sendNextUploadChunk(upload: PendingUpload, overwrite: Boolean = false) {
        coroutineScope.launch(Dispatchers.IO) {
            try {
                val inputStream: InputStream? = context.contentResolver.openInputStream(upload.uri)
                if (inputStream == null) {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(context, "Cannot open file for upload.", Toast.LENGTH_SHORT).show()
                        isTransferring = false
                    }
                    return@launch
                }

                inputStream.use { stream ->
                    if (upload.currentOffset > 0) {
                        stream.skip(upload.currentOffset)
                    }
                    val buffer = ByteArray(chunkSize)
                    val bytesRead = stream.read(buffer)
                    if (bytesRead > 0) {
                        val slice = if (bytesRead == chunkSize) buffer else buffer.copyOf(bytesRead)
                        val b64 = Base64.encodeToString(slice, Base64.NO_WRAP)
                        val newOffset = upload.currentOffset + bytesRead
                        val isComplete = (newOffset >= upload.totalSize) || (bytesRead < chunkSize)
                        val targetRemotePath = if (upload.targetDirectory.endsWith("\\") || upload.targetDirectory.endsWith("/")) {
                            "${upload.targetDirectory}${upload.filename}"
                        } else {
                            "${upload.targetDirectory}\\${upload.filename}"
                        }

                        withContext(Dispatchers.Main) {
                            activeClient?.requestWriteFileChunk(
                                deviceId = device.id,
                                path = targetRemotePath,
                                offset = upload.currentOffset,
                                base64Data = b64,
                                isComplete = isComplete,
                                overwrite = overwrite
                            )
                        }
                    } else {
                        withContext(Dispatchers.Main) {
                            isTransferring = false
                        }
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(context, "Upload error: ${e.message}", Toast.LENGTH_SHORT).show()
                    isTransferring = false
                }
            }
        }
    }

    // Connect & wire callbacks
    DisposableEffect(Unit) {
        val client: SignalingClient
        if (signalingClient != null) {
            client = signalingClient
            activeClient = client
            isLocalClient = false
        } else {
            val serverBase = tokenManager.serverUrl
            val wsUrl = serverBase.replace("http://", "ws://").replace("https://", "wss://") + "/ws/signaling"
            val token = tokenManager.authToken ?: ""
            client = SignalingClient(wsUrl, token)
            activeClient = client
            isLocalClient = true
            client.connect()
        }

        client.onFileListReceived = { path, entries, error ->
            coroutineScope.launch(Dispatchers.Main) {
                isLoading = false
                if (error != null) {
                    Toast.makeText(context, "Folder access error: $error", Toast.LENGTH_LONG).show()
                } else {
                    currentPath = path
                    filesList = (entries ?: emptyList()).sortedWith(
                        compareByDescending<FileItem> { it.isDirectory }.thenBy { it.name.lowercase() }
                    )
                }
            }
        }

        client.onFileReadChunkReceived = { path, offset, data, isEof, sha256, error ->
            coroutineScope.launch(Dispatchers.Main) {
                if (error != null) {
                    Toast.makeText(context, "Download error: $error", Toast.LENGTH_LONG).show()
                    isTransferring = false
                    try { currentDownloadOutputStream?.close() } catch (_: Exception) {}
                    return@launch
                }

                if (data != null && currentDownloadOutputStream != null) {
                    try {
                        val bytes = Base64.decode(data, Base64.DEFAULT)
                        withContext(Dispatchers.IO) {
                            currentDownloadOutputStream?.write(bytes)
                        }
                        currentDownloadReceivedSize += bytes.size
                        if (currentDownloadTotalSize > 0) {
                            transferProgress = (currentDownloadReceivedSize.toFloat() / currentDownloadTotalSize.toFloat()).coerceIn(0f, 1f)
                        }

                        if (!isEof && bytes.isNotEmpty()) {
                            // Request next chunk
                            client.requestReadFileChunk(device.id, path, offset + bytes.size, chunkSize)
                        } else {
                            // Completed
                            withContext(Dispatchers.IO) {
                                currentDownloadOutputStream?.flush()
                                currentDownloadOutputStream?.close()
                            }
                            currentDownloadOutputStream = null
                            isTransferring = false
                            Toast.makeText(context, "Downloaded successfully: ${currentDownloadFile?.name}", Toast.LENGTH_LONG).show()
                        }
                    } catch (e: Exception) {
                        Toast.makeText(context, "File write error: ${e.message}", Toast.LENGTH_SHORT).show()
                        isTransferring = false
                    }
                }
            }
        }

        client.onFileWriteChunkResponse = { path, offset, success, isComplete, error ->
            coroutineScope.launch(Dispatchers.Main) {
                if (error == "file_exists") {
                    showOverwriteDialog = true
                    return@launch
                }

                if (!success || error != null) {
                    Toast.makeText(context, "Upload failed: ${error ?: "Unknown error"}", Toast.LENGTH_LONG).show()
                    isTransferring = false
                    pendingUpload = null
                    return@launch
                }

                val upload = pendingUpload
                if (upload != null) {
                    upload.currentOffset = offset + chunkSize
                    if (upload.totalSize > 0) {
                        transferProgress = (upload.currentOffset.toFloat() / upload.totalSize.toFloat()).coerceIn(0f, 1f)
                    }

                    if (isComplete || upload.currentOffset >= upload.totalSize) {
                        isTransferring = false
                        pendingUpload = null
                        Toast.makeText(context, "Upload completed: ${upload.filename}", Toast.LENGTH_SHORT).show()
                        // Refresh directory
                        client.requestFileList(device.id, currentPath)
                    } else {
                        // Send next slice
                        sendNextUploadChunk(upload, overwrite = true)
                    }
                }
            }
        }

        client.onFileDeleteResponse = { path, success, error ->
            coroutineScope.launch(Dispatchers.Main) {
                if (success) {
                    Toast.makeText(context, "Deleted successfully.", Toast.LENGTH_SHORT).show()
                    filesList = filesList.filter { it.effectivePath != path }
                } else {
                    Toast.makeText(context, "Delete failed: ${error ?: "Permission denied"}", Toast.LENGTH_LONG).show()
                }
            }
        }

        // Trigger initial folder listing
        client.onConnected = {
            client.requestFileList(device.id, currentPath)
        }
        client.requestFileList(device.id, currentPath)

        onDispose {
            try { currentDownloadOutputStream?.close() } catch (_: Exception) {}
            if (isLocalClient) {
                client.disconnect()
            }
        }
    }

    // File picker launcher for upload
    val uploadPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        if (uri != null) {
            var filename = "upload_${System.currentTimeMillis()}"
            var fileSize = 0L

            val cursor = context.contentResolver.query(uri, null, null, null, null)
            cursor?.use {
                if (it.moveToFirst()) {
                    val nameIdx = it.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    val sizeIdx = it.getColumnIndex(OpenableColumns.SIZE)
                    if (nameIdx != -1) filename = it.getString(nameIdx) ?: filename
                    if (sizeIdx != -1) fileSize = it.getLong(sizeIdx)
                }
            }

            val upload = PendingUpload(
                uri = uri,
                filename = filename,
                totalSize = fileSize,
                targetDirectory = currentPath,
                currentOffset = 0L
            )
            pendingUpload = upload
            transferFilename = filename
            transferStatusText = "Uploading to laptop..."
            transferProgress = 0f
            isTransferring = true

            // Begin uploading with chunk 0 (initially overwrite = false to detect conflicts)
            sendNextUploadChunk(upload, overwrite = false)
        }
    }

    fun startDownload(item: FileItem) {
        try {
            val downloadsDir = context.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS)
                ?: File(context.filesDir, "downloads")
            if (!downloadsDir.exists()) downloadsDir.mkdirs()

            val localFile = File(downloadsDir, item.name)
            val outputStream = FileOutputStream(localFile)

            currentDownloadFile = localFile
            currentDownloadOutputStream = outputStream
            currentDownloadTotalSize = item.effectiveSize
            currentDownloadReceivedSize = 0L

            transferFilename = item.name
            transferStatusText = "Downloading from laptop..."
            transferProgress = 0f
            isTransferring = true

            activeClient?.requestReadFileChunk(
                deviceId = device.id,
                path = item.effectivePath,
                offset = 0L,
                length = chunkSize
            )
        } catch (e: Exception) {
            Toast.makeText(context, "Cannot start download: ${e.message}", Toast.LENGTH_SHORT).show()
        }
    }

    fun navigateUp() {
        if (currentPath.isNotEmpty()) {
            val norm = currentPath.trimEnd('\\', '/')
            val lastSlash = maxOf(norm.lastIndexOf('\\'), norm.lastIndexOf('/'))
            if (lastSlash > 0) {
                val parent = norm.substring(0, lastSlash)
                val target = if (parent.length == 2 && parent.endsWith(":")) "$parent\\" else parent
                isLoading = true
                activeClient?.requestFileList(device.id, target)
            } else if (lastSlash == 0) {
                isLoading = true
                activeClient?.requestFileList(device.id, "\\")
            } else {
                isLoading = true
                activeClient?.requestFileList(device.id, "")
            }
        }
    }

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
                        uploadPickerLauncher.launch("*/*")
                    }) {
                        Icon(Icons.Default.Upload, contentDescription = "Upload File", tint = CyanSecondary)
                    }
                    IconButton(onClick = {
                        isLoading = true
                        activeClient?.requestFileList(device.id, currentPath)
                    }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = TextPrimary)
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
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(
                        onClick = { navigateUp() },
                        enabled = currentPath.isNotEmpty() && currentPath != "C:\\" && currentPath != "C:"
                    ) {
                        Icon(
                            Icons.Default.ArrowUpward,
                            contentDescription = "Up",
                            tint = if (currentPath.isNotEmpty()) CyanSecondary else TextSecondary.copy(alpha = 0.4f)
                        )
                    }
                    Icon(Icons.Default.FolderOpen, contentDescription = null, tint = CyanSecondary, modifier = Modifier.size(20.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = if (currentPath.isEmpty()) "Authorized Root Folders" else currentPath,
                        style = MaterialTheme.typography.bodySmall,
                        color = TextPrimary,
                        maxLines = 1,
                        modifier = Modifier.weight(1f)
                    )
                }
            }

            // Progress Banner during Transfer
            if (isTransferring) {
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    colors = CardDefaults.cardColors(containerColor = CharcoalSurface),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(transferFilename, style = MaterialTheme.typography.bodyMedium, color = TextPrimary, maxLines = 1)
                                Text(transferStatusText, style = MaterialTheme.typography.bodySmall, color = TextSecondary)
                            }
                            Text("${(transferProgress * 100).toInt()}%", style = MaterialTheme.typography.titleMedium, color = CyanSecondary)
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

            // Loading Indicator
            if (isLoading) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = ElectricBluePrimary)
                }
            } else if (filesList.isEmpty()) {
                Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("No files or folders found in this directory.", color = TextSecondary, style = MaterialTheme.typography.bodyMedium)
                }
            } else {
                // File Entries List
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(filesList, key = { it.effectivePath }) { item ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    if (item.isDirectory) {
                                        isLoading = true
                                        activeClient?.requestFileList(device.id, item.effectivePath)
                                    } else {
                                        startDownload(item)
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
                                Row(
                                    modifier = Modifier.weight(1f),
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        imageVector = if (item.isDirectory) Icons.Default.Folder else Icons.Default.InsertDriveFile,
                                        contentDescription = null,
                                        tint = if (item.isDirectory) CyanSecondary else TextSecondary,
                                        modifier = Modifier.size(28.dp)
                                    )
                                    Spacer(modifier = Modifier.width(12.dp))
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(item.name, color = TextPrimary, fontWeight = FontWeight.SemiBold, fontSize = 14.sp, maxLines = 1)
                                        val sizeStr = if (item.isDirectory) "Folder" else "${item.effectiveSize / 1024} KB"
                                        Text("$sizeStr  •  ${item.modifiedAt}", color = TextSecondary, fontSize = 11.sp)
                                    }
                                }

                                Row {
                                    if (!item.isDirectory) {
                                        IconButton(onClick = { startDownload(item) }) {
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
    }

    // Overwrite Confirmation Dialog
    if (showOverwriteDialog) {
        val upload = pendingUpload
        AlertDialog(
            onDismissRequest = {
                showOverwriteDialog = false
                isTransferring = false
                pendingUpload = null
            },
            title = { Text("File Exists on Laptop") },
            text = { Text("A file named '${upload?.filename}' already exists in this folder. Do you want to overwrite it?") },
            confirmButton = {
                Button(
                    onClick = {
                        showOverwriteDialog = false
                        if (upload != null) {
                            sendNextUploadChunk(upload, overwrite = true)
                        }
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = ElectricBluePrimary)
                ) {
                    Text("Overwrite")
                }
            },
            dismissButton = {
                TextButton(onClick = {
                    showOverwriteDialog = false
                    isTransferring = false
                    pendingUpload = null
                }) {
                    Text("Cancel")
                }
            }
        )
    }

    // Confirm Delete Dialog
    fileToDelete?.let { item ->
        AlertDialog(
            onDismissRequest = { fileToDelete = null },
            title = { Text("Delete Confirmation") },
            text = { Text("Are you sure you want to delete '${item.name}' from your laptop? This action cannot be undone.") },
            confirmButton = {
                TextButton(
                    onClick = {
                        val path = item.effectivePath
                        fileToDelete = null
                        activeClient?.requestDeleteFile(device.id, path)
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
