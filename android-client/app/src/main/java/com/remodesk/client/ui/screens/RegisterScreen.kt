package com.remodesk.client.ui.screens

import android.widget.Toast
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Person
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RegisterScreen(
    tokenManager: TokenManager,
    onRegisterSuccess: () -> Unit,
    onNavigateBack: () -> Unit
) {
    val context = LocalContext.current
    val coroutineScope = rememberCoroutineScope()

    var fullName by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var serverUrl by remember { mutableStateOf(tokenManager.serverUrl) }
    var isLoading by remember { mutableStateOf(false) }

    var showVerifyDialog by remember { mutableStateOf(false) }
    var verificationCodeInput by remember { mutableStateOf("") }
    var isVerifying by remember { mutableStateOf(false) }
    var registeredTokenResp by remember { mutableStateOf<com.remodesk.client.data.TokenResponse?>(null) }


    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Create Account", color = TextPrimary) },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back", tint = TextPrimary)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkNavyBackground)
            )
        },
        containerColor = DarkNavyBackground
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            OutlinedTextField(
                value = fullName,
                onValueChange = { fullName = it },
                label = { Text("Full Name") },
                leadingIcon = { Icon(Icons.Default.Person, contentDescription = null, tint = TextSecondary) },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = ElectricBluePrimary,
                    unfocusedBorderColor = CharcoalSurfaceVariant
                )
            )

            Spacer(modifier = Modifier.height(16.dp))

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

            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = { Text("Password (min 6 chars)") },
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

            OutlinedTextField(
                value = confirmPassword,
                onValueChange = { confirmPassword = it },
                label = { Text("Confirm Password") },
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


            OutlinedTextField(
                value = serverUrl,
                onValueChange = {
                    serverUrl = it
                    tokenManager.serverUrl = it
                },
                label = { Text("Gateway Server URL") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = CyanSecondary,
                    unfocusedBorderColor = CharcoalSurfaceVariant
                )
            )

            Spacer(modifier = Modifier.height(28.dp))


            Button(
                onClick = {
                    if (email.isBlank() || password.isBlank()) {
                        Toast.makeText(context, "All fields are required.", Toast.LENGTH_SHORT).show()
                        return@Button
                    }
                    if (password != confirmPassword) {
                        Toast.makeText(context, "Passwords do not match.", Toast.LENGTH_SHORT).show()
                        return@Button
                    }
                    isLoading = true
                    coroutineScope.launch {
                        try {
                            val api = ApiService.create(serverUrl, tokenManager)

                            val resp = api.register(mapOf(
                                "email" to email.trim(),
                                "password" to password,
                                "full_name" to fullName.trim()
                            ))
                            registeredTokenResp = resp
                            tokenManager.authToken = resp.accessToken
                            tokenManager.refreshToken = resp.refreshToken
                            tokenManager.userEmail = email.trim()

                            if (!resp.user.isVerified) {
                                showVerifyDialog = true
                                Toast.makeText(context, "Verification code sent to email.", Toast.LENGTH_LONG).show()
                            } else {
                                Toast.makeText(context, "Account created successfully!", Toast.LENGTH_SHORT).show()
                                onRegisterSuccess()
                            }
                        } catch (e: Exception) {
                            Toast.makeText(context, "Registration failed: ${e.message}", Toast.LENGTH_LONG).show()
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
                    Text("Register & Sign In", fontSize = 16.sp, fontWeight = FontWeight.SemiBold)
                }
            }
        }

        // Email Verification Dialog
        if (showVerifyDialog) {
            AlertDialog(
                onDismissRequest = { /* Require verification */ },
                title = { Text("Verify Your Email", color = TextPrimary, fontWeight = FontWeight.Bold) },
                text = {
                    Column {
                        Text(
                            "A 6-digit verification code has been generated for $email. Please enter it below to activate your account.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = TextSecondary
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        OutlinedTextField(
                            value = verificationCodeInput,
                            onValueChange = { verificationCodeInput = it.take(10) },
                            label = { Text("6-Digit Code") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
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
                            if (verificationCodeInput.isBlank()) return@Button
                            isVerifying = true
                            coroutineScope.launch {
                                try {
                                    val api = ApiService.create(serverUrl, tokenManager)
                                    api.verifyEmail(mapOf(
                                        "email" to email.trim(),
                                        "code" to verificationCodeInput.trim()
                                    ))
                                    Toast.makeText(context, "Email verified successfully!", Toast.LENGTH_SHORT).show()
                                    showVerifyDialog = false
                                    onRegisterSuccess()
                                } catch (e: Exception) {
                                    Toast.makeText(context, "Verification failed: ${e.message}", Toast.LENGTH_LONG).show()
                                } finally {
                                    isVerifying = false
                                }
                            }
                        },
                        enabled = !isVerifying && verificationCodeInput.isNotBlank(),
                        colors = ButtonDefaults.buttonColors(containerColor = ElectricBluePrimary)
                    ) {
                        Text(if (isVerifying) "Verifying..." else "Verify & Continue")
                    }
                },
                dismissButton = {
                    TextButton(
                        onClick = {
                            coroutineScope.launch {
                                try {
                                    val api = ApiService.create(serverUrl, tokenManager)
                                    api.resendVerification(mapOf("email" to email.trim()))
                                    Toast.makeText(context, "New code sent to email.", Toast.LENGTH_SHORT).show()
                                } catch (e: Exception) {
                                    Toast.makeText(context, "Resend failed: ${e.message}", Toast.LENGTH_SHORT).show()
                                }
                            }
                        }
                    ) {
                        Text("Resend Code", color = CyanSecondary)
                    }
                },
                containerColor = CharcoalSurface
            )
        }
    }
}
