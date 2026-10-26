using System;
using System.Collections.Generic;
using System.Drawing;
using System.Threading;
using System.Threading.Tasks;
using RemoDesk.Host.Capture;
using RemoDesk.Host.Input;
using SIPSorcery.Net;

namespace RemoDesk.Host.WebRtc
{
    public class WebRtcSessionManager : IDisposable
    {
        private RTCPeerConnection? _peerConnection;
        private RTCDataChannel? _dataChannel;
        private readonly IScreenCapturer _screenCapturer;
        private readonly IInputInjector _inputInjector;
        private readonly DataChannelProtocol _protocol;
        private readonly Func<bool> _isControlAllowed;
        private CancellationTokenSource? _captureCts;
        private bool _isStreaming;
        private volatile int _targetDelayMs = 33;

        public event Action<string>? OnIceCandidateGenerated;
        public event Action<string>? OnSessionClosed;
        public event Action<string>? OnFrameDataReady; // Fallback or direct frame transmitter

        public string CurrentSessionId { get; private set; } = string.Empty;

        public WebRtcSessionManager(
            IScreenCapturer screenCapturer,
            IInputInjector inputInjector,
            Func<bool> isControlAllowed)
        {
            _screenCapturer = screenCapturer;
            _inputInjector = inputInjector;
            _isControlAllowed = isControlAllowed;
            _protocol = new DataChannelProtocol(inputInjector, isControlAllowed);

            try
            {
                Microsoft.Win32.SystemEvents.DisplaySettingsChanged += OnDisplaySettingsChanged;
            }
            catch { }
        }

        private void OnDisplaySettingsChanged(object? sender, EventArgs e)
        {
            Console.WriteLine("[WebRTC] Display settings or resolution changed, adapting screen capturer...");
            _screenCapturer.Reinitialize();
        }

        public void SetStreamingQuality(int targetFps, int jpegQuality)
        {
            _targetDelayMs = 1000 / Math.Clamp(targetFps, 10, 60);
            _screenCapturer.SetQuality(jpegQuality);
            Console.WriteLine($"[WebRTC] Adapted streaming parameters: FPS={targetFps}, Quality={jpegQuality}");
        }

        public void SelectMonitor(int monitorIndex)
        {
            _screenCapturer.SetMonitor(monitorIndex);
        }

        public async Task<string> HandleOfferAsync(string sessionId, string sdpOffer, List<RTCIceServer> iceServers)
        {
            CurrentSessionId = sessionId;
            DisposeCurrentPeer();

            var config = new RTCConfiguration
            {
                iceServers = iceServers,
            };

            _peerConnection = new RTCPeerConnection(config);

            // Handle incoming data channel
            _peerConnection.ondatachannel += (channel) =>
            {
                _dataChannel = channel;
                _dataChannel.onmessage += (dc, proto, data) =>
                {
                    string msg = System.Text.Encoding.UTF8.GetString(data);
                    _protocol.HandleMessage(msg);
                };
                _protocol.OnSendMessage += (outMsg) =>
                {
                    if (_dataChannel != null && _dataChannel.readyState == RTCDataChannelState.open)
                    {
                        _dataChannel.send(outMsg);
                    }
                };
            };

            // Forward ICE candidates
            _peerConnection.onicecandidate += (candidate) =>
            {
                if (candidate != null)
                {
                    OnIceCandidateGenerated?.Invoke(candidate.toJSON());
                }
            };

            _peerConnection.onconnectionstatechange += (state) =>
            {
                Console.WriteLine($"[WebRTC] PeerConnection state: {state}");
                if (state == RTCPeerConnectionState.closed || state == RTCPeerConnectionState.failed)
                {
                    StopStreaming();
                    OnSessionClosed?.Invoke(CurrentSessionId);
                }
                else if (state == RTCPeerConnectionState.connected)
                {
                    StartStreaming();
                }
            };

            // Set remote offer
            var result = _peerConnection.setRemoteDescription(new RTCSessionDescriptionInit
            {
                type = RTCSdpType.offer,
                sdp = sdpOffer,
            });

            if (result != SetDescriptionResultEnum.OK)
            {
                throw new InvalidOperationException($"Failed to set remote description: {result}");
            }

            // Create local answer
            var answer = _peerConnection.createAnswer(null);
            await _peerConnection.setLocalDescription(answer);

            return answer.sdp;
        }

        public void AddIceCandidate(string candidateJson)
        {
            try
            {
                if (_peerConnection != null)
                {
                    var init = new RTCIceCandidateInit { candidate = candidateJson };
                    _peerConnection.addIceCandidate(init);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error adding ICE candidate: {ex.Message}");
            }
        }

        public void StartStreaming(int targetFps = 30)
        {
            if (_isStreaming) return;
            _isStreaming = true;
            _captureCts = new CancellationTokenSource();

            _targetDelayMs = 1000 / Math.Clamp(targetFps, 10, 60);

            Task.Run(async () =>
            {
                while (!_captureCts.Token.IsCancellationRequested && _isStreaming)
                {
                    try
                    {
                        var frame = _screenCapturer.CaptureFrame();
                        if (frame != null && frame.CompressedBytes != null)
                        {
                            // If data channel is open, we can send preview frames or raw stream
                            string base64 = Convert.ToBase64String(frame.CompressedBytes);
                            OnFrameDataReady?.Invoke(base64);
                            frame.Dispose();
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Capture loop error: {ex.Message}");
                    }

                    await Task.Delay(_targetDelayMs, _captureCts.Token);
                }
            }, _captureCts.Token);
        }

        public void StopStreaming()
        {
            _isStreaming = false;
            _captureCts?.Cancel();
        }

        private void DisposeCurrentPeer()
        {
            StopStreaming();
            _dataChannel?.close();
            _peerConnection?.close();
            _peerConnection?.Dispose();
            _peerConnection = null;
        }

        public void Dispose()
        {
            try
            {
                Microsoft.Win32.SystemEvents.DisplaySettingsChanged -= OnDisplaySettingsChanged;
            }
            catch { }
            DisposeCurrentPeer();
            _screenCapturer.Dispose();
        }
    }
}
