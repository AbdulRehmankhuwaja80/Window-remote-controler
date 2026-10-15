package com.remodesk.client.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Sensors
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.remodesk.client.data.TokenManager
import com.remodesk.client.network.ApiService
import com.remodesk.client.ui.theme.*
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(
    tokenManager: TokenManager,
    onLoginSuccess: () -> Unit,
    onNavigateToRegister: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var email by remember { mutableStateOf(tokenManager.userEmail ?: "") }
    var password by remember { mutableStateOf("") }
    var serverUrl by remember { mutableStateOf(tokenManager.serverUrl) }
    var isLoading by remember { mutableStateOf(false) }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(DarkNavyBackground)
            .padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.fillMaxWidth()
        ) {
            // App Branding Icon
            Surface(
                modifier = Modifier.size(72.dp),
                shape = RoundedCornerShape(20.dp),
                color = ElectricBluePrimary.copy(alpha = 0.15f)
            ) {
                Box(contentAlignment = Alignment.Center) {
                    Icon(
                        imageVector = Icons.Default.Sensors,
                        contentDescription = "Logo",
                        tint = ElectricBluePrimary,
                        modifier = Modifier.size(40.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            Text(
                text = "RemoDesk",
                style = MaterialTheme.typography.headlineMedium,
                fontWeight = FontWeight.Bold,
                color = TextPrimary
            )
            Text(
                text = "Remote Laptop Control from Anywhere",
                style = MaterialTheme.typography.bodyMedium,
                color = TextSecondary
            )

            Spacer(modifier = Modifier.height(32.dp))

            // Email Input
            OutlinedTextField(
                value = email,
                onValueChange = { email = it },
                label = { Text("Email Address") },
                leadingIcon = { Icon(Icons.Default.Email, contentDescription = null, tint = TextSecondary) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = ElectricBluePrimary,
                    unfocusedBorderColor = CharcoalSurfaceVariant
                )
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Password Input
            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = { Text("Password") },
                leadingIcon = { Icon(Icons.Default.Lock, contentDescription = null, tint = TextSecondary) },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = ElectricBluePrimary,
                    unfocusedBorderColor = CharcoalSurfaceVariant
                )
            )

            Spacer(modifier = Modifier.height(16.dp))

            // Gateway Server URL Config
            OutlinedTextField(
                value = serverUrl,
                onValueChange = {
                    serverUrl = it
                    tokenManager.serverUrl = it
                },
                label = { Text("Cloud Gateway / Server URL") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = CyanSecondary,
                    unfocusedBorderColor = CharcoalSurfaceVariant
                )
            )

            Spacer(modifier = Modifier.height(28.dp))

            // Sign In Button
            Button(
                onClick = {
                    if (email.isBlank() || password.isBlank()) {
                        Toast.makeText(context, "Please enter email and password.", Toast.LENGTH_SHORT).show()
                        return@Button
                    }
                    isLoading = true
                    coroutineScope.launch {
                        try {
                            val api = ApiService.create(serverUrl, tokenManager)
                            val resp = api.login(mapOf("email" to email.trim(), "password" to password))
                            tokenManager.authToken = resp.accessToken
                            tokenManager.userEmail = email.trim()
                            Toast.makeText(context, "Welcome back, ${resp.user.fullName ?: "User"}!", Toast.LENGTH_SHORT).show()
                            onLoginSuccess()
                        } catch (e: Exception) {
                            Toast.makeText(context, "Login failed: ${e.message}", Toast.LENGTH_LONG).show()
                        } finally {
                            isLoading = false
                        }
                    }
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = ElectricBluePrimary),
                enabled = !isLoading
            ) {
                if (isLoading) {
                    CircularProgressIndicator(color = Color.White, modifier = Modifier.size(24.dp))
                } else {
                    Text("Sign In", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Create Account link
            TextButton(onClick = onNavigateToRegister) {
                Text(
                    text = "Don't have an account? Create one",
                    color = ElectricBluePrimary,
                    fontSize = 14.sp
                )
            }
        }
    }
}
