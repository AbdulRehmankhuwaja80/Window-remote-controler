package com.remodesk.client.network

import com.remodesk.client.data.*
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

interface ApiService {

    @POST("/api/auth/register")
    suspend fun register(@Body body: Map<String, String>): TokenResponse

    @POST("/api/auth/login")
    suspend fun login(@Body body: Map<String, String>): TokenResponse

    @GET("/api/auth/me")
    suspend fun getProfile(): User

    @GET("/api/devices")
    suspend fun listDevices(): List<Device>

    @GET("/api/devices/{id}")
    suspend fun getDevice(@Path("id") deviceId: String): Device

    @PATCH("/api/devices/{id}")
    suspend fun updateDevice(
        @Path("id") deviceId: String,
        @Body body: Map<String, Any>
    ): Device

    @DELETE("/api/devices/{id}")
    suspend fun deleteDevice(@Path("id") deviceId: String)

    @GET("/api/sessions/ice-servers")
    suspend fun getIceServers(): WebRtcConfig

    @POST("/api/sessions/start")
    suspend fun startSession(@Body body: Map<String, String>): SessionStartResponse

    companion object {
        fun create(baseUrl: String, tokenManager: TokenManager): ApiService {
            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }

            val client = OkHttpClient.Builder()
                .connectTimeout(15, TimeUnit.SECONDS)
                .readTimeout(15, TimeUnit.SECONDS)
                .addInterceptor(logging)
                .addInterceptor { chain ->
                    val reqBuilder = chain.request().newBuilder()
                    tokenManager.authToken?.let { token ->
                        reqBuilder.addHeader("Authorization", "Bearer $token")
                    }
                    chain.proceed(reqBuilder.build())
                }
                .build()

            val normalizedUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"

            return Retrofit.Builder()
                .baseUrl(normalizedUrl)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(ApiService::class.java)
        }
    }
}
