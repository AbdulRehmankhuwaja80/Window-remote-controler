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
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
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

    // Forgot password state
    var showForgotPasswordDialog by remember { mutableStateOf(false) }
    var forgotPasswordEmail by remember { mutableStateOf("") }
    var resetTokenInput by remember { mutableStateOf("") }
    var newPasswordInput by remember { mutableStateOf("") }
    var resetStage by remember { mutableStateOf(1) } // 1 = request token, 2 = enter token & new password
    var isResetting by remember { mutableStateOf(false) }

    // Verification prompt state
    var showVerificationDialog by remember { mutableStateOf(false) }
    var verificationCodeInput by remember { mutableStateOf("") }
    var isVerifying by remember { mutableStateOf(false) }

    fun triggerBiometricAuth() {
        if (context is FragmentActivity && tokenManager.authToken != null) {
            val executor = ContextCompat.getMainExecutor(context)
            val prompt = BiometricPrompt(
                context,
                executor,
                object : BiometricPrompt.AuthenticationCallback() {
                    override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                        super.onAuthenticationSucceeded(result)
                        Toast.makeText(context, "Biometric authentication successful!", Toast.LENGTH_SHORT).show()
                        onLoginSuccess()
                    }

                    override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                        super.onAuthenticationError(errorCode, errString)
                        Toast.makeText(context, "Biometric error: $errString", Toast.LENGTH_SHORT).show()
                    }
                }
            )

            val promptInfo = BiometricPrompt.PromptInfo.Builder()
                .setTitle("Unlock RemoDesk")
                .setSubtitle("Authenticate using fingerprint or face recognition")
                .setNegativeButtonText("Use Password")
                .build()

            prompt.authenticate(promptInfo)
        }
    }

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
                            tokenManager.refreshToken = resp.refreshToken
                            tokenManager.userEmail = email.trim()
                            Toast.makeText(context, "Welcome back, ${resp.user.fullName ?: "User"}!", Toast.LENGTH_SHORT).show()
                            onLoginSuccess()
                        } catch (e: Exception) {
                            val msg = e.message ?: "Unknown error"
                            if (msg.contains("verify", ignoreCase = true) || msg.contains("verification", ignoreCase = true)) {
                                showVerificationDialog = true
                                Toast.makeText(context, "Please verify your email address.", Toast.LENGTH_LONG).show()
                            } else {
                                Toast.makeText(context, "Login failed: $msg", Toast.LENGTH_LONG).show()
                            }
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

            // Biometric Quick Unlock if enabled
            if (tokenManager.isBiometricEnabled && tokenManager.authToken != null) {
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedButton(
                    onClick = { triggerBiometricAuth() },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(48.dp),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = CyanSecondary)
                ) {
                    Icon(Icons.Default.Sensors, contentDescription = "Biometric", modifier = Modifier.size(18.dp))
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Unlock with Biometrics (Fingerprint/Face)")
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Forgot Password link
                TextButton(onClick = {
                    forgotPasswordEmail = email
                    resetStage = 1
                    showForgotPasswordDialog = true
                }) {
                    Text("Forgot Password?", color = TextSecondary, fontSize = 13.sp)
                }

                // Create Account link
                TextButton(onClick = onNavigateToRegister) {
                    Text("Create Account", color = ElectricBluePrimary, fontSize = 13.sp)
                }
            }
        }

        // Email Verification Dialog
        if (showVerificationDialog) {
            AlertDialog(
                onDismissRequest = { showVerificationDialog = false },
                title = { Text("Email Verification Required", color = TextPrimary, fontWeight = FontWeight.Bold) },
                text = {
                    Column {
                        Text(
                            "Enter the 6-digit verification code sent to $email:",
                            style = MaterialTheme.typography.bodyMedium,
                            color = TextSecondary
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        OutlinedTextField(
                            value = verificationCodeInput,
                            onValueChange = { verificationCodeInput = it.take(10) },
                            label = { Text("Verification Code") },
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
                                    api.verifyEmail(mapOf("email" to email.trim(), "code" to verificationCodeInput.trim()))
                                    Toast.makeText(context, "Email verified! You can now sign in.", Toast.LENGTH_SHORT).show()
                                    showVerificationDialog = false
                                } catch (e: Exception) {
                                    Toast.makeText(context, "Verification error: ${e.message}", Toast.LENGTH_LONG).show()
                                } finally {
                                    isVerifying = false
                                }
                            }
                        },
                        enabled = !isVerifying,
                        colors = ButtonDefaults.buttonColors(containerColor = ElectricBluePrimary)
                    ) {
                        Text(if (isVerifying) "Verifying..." else "Verify")
                    }
                },
                dismissButton = {
                    TextButton(
                        onClick = {
                            coroutineScope.launch {
                                try {
                                    val api = ApiService.create(serverUrl, tokenManager)
                                    api.resendVerification(mapOf("email" to email.trim()))
                                    Toast.makeText(context, "New verification code requested.", Toast.LENGTH_SHORT).show()
                                } catch (e: Exception) {
                                    Toast.makeText(context, "Failed: ${e.message}", Toast.LENGTH_LONG).show()
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

        // Forgot / Reset Password Dialog
        if (showForgotPasswordDialog) {
            AlertDialog(
                onDismissRequest = { if (!isResetting) showForgotPasswordDialog = false },
                title = {
                    Text(
                        if (resetStage == 1) "Reset Your Password" else "Enter New Password",
                        color = TextPrimary,
                        fontWeight = FontWeight.Bold
                    )
                },
                text = {
                    Column {
                        if (resetStage == 1) {
                            Text(
                                "Enter your registered email address to receive password reset instructions.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = TextSecondary
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            OutlinedTextField(
                                value = forgotPasswordEmail,
                                onValueChange = { forgotPasswordEmail = it },
                                label = { Text("Email Address") },
                                singleLine = true,
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email),
                                modifier = Modifier.fillMaxWidth()
                            )
                        } else {
                            Text(
                                "Enter the reset token received and choose your new password.",
                                style = MaterialTheme.typography.bodyMedium,
                                color = TextSecondary
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            OutlinedTextField(
                                value = resetTokenInput,
                                onValueChange = { resetTokenInput = it },
                                label = { Text("Reset Token") },
                                singleLine = true,
                                modifier = Modifier.fillMaxWidth()
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            OutlinedTextField(
                                value = newPasswordInput,
                                onValueChange = { newPasswordInput = it },
                                label = { Text("New Password (min 6 chars)") },
                                singleLine = true,
                                visualTransformation = PasswordVisualTransformation(),
                                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                                modifier = Modifier.fillMaxWidth()
                            )
                        }
                    }
                },
                confirmButton = {
                    Button(
                        onClick = {
                            isResetting = true
                            coroutineScope.launch {
                                try {
                                    val api = ApiService.create(serverUrl, tokenManager)
                                    if (resetStage == 1) {
                                        api.forgotPassword(mapOf("email" to forgotPasswordEmail.trim()))
                                        Toast.makeText(context, "Reset instructions sent to email.", Toast.LENGTH_SHORT).show()
                                        resetStage = 2
                                    } else {
                                        api.resetPassword(mapOf(
                                            "token" to resetTokenInput.trim(),
                                            "new_password" to newPasswordInput
                                        ))
                                        Toast.makeText(context, "Password reset successful! Please log in.", Toast.LENGTH_LONG).show()
                                        showForgotPasswordDialog = false
                                        password = ""
                                    }
                                } catch (e: Exception) {
                                    Toast.makeText(context, "Error: ${e.message}", Toast.LENGTH_LONG).show()
                                } finally {
                                    isResetting = false
                                }
                            }
                        },
                        enabled = !isResetting,
                        colors = ButtonDefaults.buttonColors(containerColor = ElectricBluePrimary)
                    ) {
                        Text(if (isResetting) "Processing..." else if (resetStage == 1) "Send Reset Token" else "Set New Password")
                    }
                },
                dismissButton = {
                    TextButton(onClick = { showForgotPasswordDialog = false }, enabled = !isResetting) {
                        Text("Cancel", color = TextSecondary)
                    }
                },
                containerColor = CharcoalSurface
            )
        }
    }
}
