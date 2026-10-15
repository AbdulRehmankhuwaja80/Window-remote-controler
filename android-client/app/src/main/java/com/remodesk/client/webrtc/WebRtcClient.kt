package com.remodesk.client.webrtc

import android.content.Context
import android.util.Log
import com.remodesk.client.data.IceServer
import org.webrtc.*
import java.nio.ByteBuffer
import java.nio.charset.StandardCharsets

class WebRtcClient(
    private val context: Context,
    private val eglBase: EglBase
) {
    private val TAG = "WebRtcClient"

    private var peerConnectionFactory: PeerConnectionFactory? = null
    private var peerConnection: PeerConnection? = null
    private var dataChannel: DataChannel? = null

    var onIceCandidateGenerated: ((candidate: String) -> Unit)? = null
    var onDataChannelStateChange: ((isOpen: Boolean) -> Unit)? = null
    var onRemoteVideoTrackReceived: ((VideoTrack) -> Unit)? = null
    var onConnectionStateChange: ((PeerConnection.PeerConnectionState) -> Unit)? = null
    var onMessageReceived: ((String) -> Unit)? = null

    init {
        initFactory()
    }

    private fun initFactory() {
        val options = PeerConnectionFactory.InitializationOptions.builder(context)
            .setEnableInternalTracer(true)
            .createInitializationOptions()
        PeerConnectionFactory.initialize(options)

        val defaultVideoEncoderFactory = DefaultVideoEncoderFactory(
            eglBase.eglBaseContext,
            true, // enableIntelVp8Encoder
            true  // enableH264HighProfile
        )

        val defaultVideoDecoderFactory = DefaultVideoDecoderFactory(eglBase.eglBaseContext)

        peerConnectionFactory = PeerConnectionFactory.builder()
            .setVideoEncoderFactory(defaultVideoEncoderFactory)
            .setVideoDecoderFactory(defaultVideoDecoderFactory)
            .createPeerConnectionFactory()
    }

    fun createPeerConnection(iceServersList: List<IceServer>) {
        val rtcIceServers = iceServersList.map { s ->
            val builder = PeerConnection.IceServer.builder(s.urls)
            if (!s.username.isNullOrEmpty() && !s.credential.isNullOrEmpty()) {
                builder.setUsername(s.username)
                builder.setPassword(s.credential)
            }
            builder.createIceServer()
        }

        val rtcConfig = PeerConnection.RTCConfiguration(rtcIceServers).apply {
            sdpSemantics = PeerConnection.SdpSemantics.UNIFIED_PLAN
            continualGatheringPolicy = PeerConnection.ContinualGatheringPolicy.GATHER_CONTINUALLY
            iceTransportsType = PeerConnection.IceTransportsType.ALL
        }

        val observer = object : PeerConnection.Observer {
            override fun onSignalingChange(state: PeerConnection.SignalingState?) {}

            override fun onIceConnectionChange(state: PeerConnection.IceConnectionState?) {
                Log.d(TAG, "ICE connection state: $state")
            }

            override fun onConnectionChange(newState: PeerConnection.PeerConnectionState?) {
                Log.d(TAG, "PeerConnection state changed: $newState")
                newState?.let { onConnectionStateChange?.invoke(it) }
            }

            override fun onIceConnectionReceivingChange(receiving: Boolean) {}

            override fun onIceGatheringChange(state: PeerConnection.IceGatheringState?) {}

            override fun onIceCandidate(candidate: IceCandidate?) {
                candidate?.let {
                    val json = "{\"sdpMid\":\"${it.sdpMid}\",\"sdpMLineIndex\":${it.sdpMLineIndex},\"candidate\":\"${it.sdp}\"}"
                    onIceCandidateGenerated?.invoke(json)
                }
            }

            override fun onIceCandidatesRemoved(candidates: Array<out IceCandidate>?) {}

            override fun onAddStream(stream: MediaStream?) {}

            override fun onRemoveStream(stream: MediaStream?) {}

            override fun onDataChannel(dc: DataChannel?) {
                setupDataChannel(dc)
            }

            override fun onRenegotiationNeeded() {}

            override fun onAddTrack(receiver: RtpReceiver?, streams: Array<out MediaStream>?) {
                val track = receiver?.track()
                if (track is VideoTrack) {
                    onRemoteVideoTrackReceived?.invoke(track)
                }
            }
        }

        peerConnection = peerConnectionFactory?.createPeerConnection(rtcConfig, observer)

        // Create initial DataChannel for sending inputs immediately
        val init = DataChannel.Init().apply {
            ordered = true
            maxRetransmits = -1
        }
        val dc = peerConnection?.createDataChannel("remodesk-control", init)
        setupDataChannel(dc)
    }

    private fun setupDataChannel(dc: DataChannel?) {
        dataChannel = dc
        dataChannel?.registerObserver(object : DataChannel.Observer {
            override fun onBufferedAmountChange(previousAmount: Long) {}

            override fun onStateChange() {
                val isOpen = dataChannel?.state() == DataChannel.State.OPEN
                Log.d(TAG, "DataChannel state: ${dataChannel?.state()}")
                onDataChannelStateChange?.invoke(isOpen)
            }

            override fun onMessage(buffer: DataChannel.Buffer?) {
                buffer?.let {
                    val bytes = ByteArray(it.data.remaining())
                    it.data.get(bytes)
                    val text = String(bytes, StandardCharsets.UTF_8)
                    onMessageReceived?.invoke(text)
                }
            }
        })
    }

    fun createOffer(callback: (sdp: String) -> Unit) {
        val constraints = MediaConstraints().apply {
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveVideo", "true"))
            mandatory.add(MediaConstraints.KeyValuePair("OfferToReceiveAudio", "false"))
        }

        peerConnection?.createOffer(object : SdpObserver {
            override fun onCreateSuccess(desc: SessionDescription?) {
                desc?.let {
                    peerConnection?.setLocalDescription(object : SdpObserver {
                        override fun onCreateSuccess(p0: SessionDescription?) {}
                        override fun onSetSuccess() {
                            callback(it.description)
                        }
                        override fun onCreateFailure(p0: String?) {}
                        override fun onSetFailure(p0: String?) {}
                    }, it)
                }
            }
            override fun onSetSuccess() {}
            override fun onCreateFailure(error: String?) {
                Log.e(TAG, "Create offer failed: $error")
            }
            override fun onSetFailure(p0: String?) {}
        }, constraints)
    }

    fun handleRemoteAnswer(sdp: String) {
        val desc = SessionDescription(SessionDescription.Type.ANSWER, sdp)
        peerConnection?.setRemoteDescription(object : SdpObserver {
            override fun onCreateSuccess(p0: SessionDescription?) {}
            override fun onSetSuccess() {
                Log.d(TAG, "Remote answer set successfully")
            }
            override fun onCreateFailure(p0: String?) {}
            override fun onSetFailure(error: String?) {
                Log.e(TAG, "Set remote answer failed: $error")
            }
        }, desc)
    }

    fun addRemoteIceCandidate(sdpMid: String, sdpMLineIndex: Int, candidateSdp: String) {
        val candidate = IceCandidate(sdpMid, sdpMLineIndex, candidateSdp)
        peerConnection?.addIceCandidate(candidate)
    }

    fun sendInputMessage(json: String) {
        if (dataChannel?.state() == DataChannel.State.OPEN) {
            val bytes = json.toByteArray(StandardCharsets.UTF_8)
            val buffer = DataChannel.Buffer(ByteBuffer.wrap(bytes), false)
            dataChannel?.send(buffer)
        }
    }

    fun close() {
        dataChannel?.close()
        dataChannel?.dispose()
        peerConnection?.close()
        peerConnection?.dispose()
        peerConnection = null
        dataChannel = null
    }
}
