using System;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace RemoDesk.Host.Signaling
{
    public class SignalingClient : IDisposable
    {
        private ClientWebSocket? _ws;
        private CancellationTokenSource? _cts;
        private readonly HostSettings _settings;
        private bool _isConnecting;

        public event Action<string, string, string>? OnSessionRequested; // sessionId, clientId, clientInfo
        public event Action<string, string>? OnOfferReceived; // sessionId, sdp
        public event Action<string, string>? OnAnswerReceived; // sessionId, sdp
        public event Action<string, string>? OnCandidateReceived; // sessionId, candidate
        public event Action<string, string>? OnSessionTerminated; // sessionId, reason
        public event Action<string>? OnInputMessageReceived; // json input from client
        public event Action<bool>? OnConnectionStateChanged; // isConnected


        public bool IsConnected => _ws?.State == WebSocketState.Open;

        public SignalingClient(HostSettings settings)
        {
            _settings = settings;
        }

        public async Task StartAsync()
        {
            if (_isConnecting || IsConnected) return;
            _isConnecting = true;
            _cts = new CancellationTokenSource();

            _ = Task.Run(() => ConnectLoopAsync(_cts.Token));
        }

        private async Task ConnectLoopAsync(CancellationToken token)
        {
            while (!token.IsCancellationRequested)
            {
                try
                {
                    _ws?.Dispose();
                    _ws = new ClientWebSocket();

                    string uriStr = $"{_settings.SignalingWsUrl}?role=host&device_id={Uri.EscapeDataString(_settings.DeviceId)}&auth_key={Uri.EscapeDataString(_settings.AuthKey)}";
                    var uri = new Uri(uriStr);

                    Console.WriteLine($"[Signaling] Connecting to {uri.Host}:{uri.Port}...");
                    await _ws.ConnectAsync(uri, token);

                    Console.WriteLine("[Signaling] Connected to gateway.");
                    OnConnectionStateChanged?.Invoke(true);

                    // Start ping task
                    _ = Task.Run(() => PingLoopAsync(token));

                    // Receive loop
                    await ReceiveLoopAsync(token);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[Signaling] Connection error: {ex.Message}");
                    OnConnectionStateChanged?.Invoke(false);
                }

                if (!token.IsCancellationRequested)
                {
                    await Task.Delay(3000, token); // Retry backoff
                }
            }
        }

        private async Task PingLoopAsync(CancellationToken token)
        {
            while (!token.IsCancellationRequested && IsConnected)
            {
                try
                {
                    await Task.Delay(15000, token);
                    if (IsConnected)
                    {
                        await SendMessageAsync(new { type = "ping" });
                    }
                }
                catch { }
            }
        }

        private async Task ReceiveLoopAsync(CancellationToken token)
        {
            var buffer = new byte[65536];
            while (!token.IsCancellationRequested && IsConnected)
            {
                var sb = new StringBuilder();
                WebSocketReceiveResult result;
                do
                {
                    result = await _ws!.ReceiveAsync(new ArraySegment<byte>(buffer), token);
                    if (result.MessageType == WebSocketMessageType.Close)
                    {
                        await _ws.CloseAsync(WebSocketCloseStatus.NormalClosure, "Closing", token);
                        OnConnectionStateChanged?.Invoke(false);
                        return;
                    }
                    sb.Append(Encoding.UTF8.GetString(buffer, 0, result.Count));
                } while (!result.EndOfMessage);

                string message = sb.ToString();
                ProcessMessage(message);
            }
        }

        private void ProcessMessage(string messageJson)
        {
            try
            {
                var jObj = JObject.Parse(messageJson);
                string type = jObj.Value<string>("type") ?? string.Empty;

                switch (type)
                {
                    case "registered":
                        Console.WriteLine($"[Signaling] Device registered successfully: {jObj.Value<string>("device_id")}");
                        break;

                    case "incoming_session_request":
                        string sId = jObj.Value<string>("session_id") ?? string.Empty;
                        string cId = jObj.Value<string>("client_id") ?? string.Empty;
                        string info = jObj.Value<string>("client_info") ?? "Android Mobile";
                        OnSessionRequested?.Invoke(sId, cId, info);
                        break;

                    case "webrtc_offer":
                        OnOfferReceived?.Invoke(
                            jObj.Value<string>("session_id") ?? string.Empty,
                            jObj.Value<string>("sdp") ?? string.Empty
                        );
                        break;

                    case "webrtc_answer":
                        OnAnswerReceived?.Invoke(
                            jObj.Value<string>("session_id") ?? string.Empty,
                            jObj.Value<string>("sdp") ?? string.Empty
                        );
                        break;

                    case "ice_candidate":
                        OnCandidateReceived?.Invoke(
                            jObj.Value<string>("session_id") ?? string.Empty,
                            jObj.Value<string>("candidate") ?? string.Empty
                        );
                        break;

                    case "session_terminated":
                        OnSessionTerminated?.Invoke(
                            jObj.Value<string>("session_id") ?? string.Empty,
                            jObj.Value<string>("reason") ?? "Terminated"
                        );
                        break;

                    case "mouse_move":
                    case "mouse_delta":
                    case "mouse_button":
                    case "mouse_scroll":
                    case "key_event":
                    case "text_input":
                    case "clipboard_sync":
                        OnInputMessageReceived?.Invoke(messageJson);
                        break;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[Signaling] Failed to parse message: {ex.Message}");
            }
        }

        public async Task SendMessageAsync(object message)
        {
            if (!IsConnected) return;
            string json = JsonConvert.SerializeObject(message);
            byte[] bytes = Encoding.UTF8.GetBytes(json);
            await _ws!.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None);
        }

        public async Task SendDesktopFrameAsync(string base64Data)
        {
            await SendMessageAsync(new
            {
                type = "desktop_frame",
                data = base64Data,
            });
        }


        public async Task AcceptSessionAsync(string sessionId, string clientId)
        {
            await SendMessageAsync(new
            {
                type = "session_response",
                session_id = sessionId,
                client_id = clientId,
                accepted = true,
            });
        }

        public async Task RejectSessionAsync(string sessionId, string clientId, string reason)
        {
            await SendMessageAsync(new
            {
                type = "session_response",
                session_id = sessionId,
                client_id = clientId,
                accepted = false,
                reason = reason,
            });
        }

        public async Task SendSdpAnswerAsync(string sessionId, string sdp)
        {
            await SendMessageAsync(new
            {
                type = "webrtc_answer",
                session_id = sessionId,
                sdp = sdp,
            });
        }

        public async Task SendIceCandidateAsync(string sessionId, string candidate)
        {
            await SendMessageAsync(new
            {
                type = "ice_candidate",
                session_id = sessionId,
                candidate = candidate,
            });
        }

        public async Task TerminateSessionAsync(string sessionId, string reason = "Host terminated session")
        {
            await SendMessageAsync(new
            {
                type = "session_end",
                session_id = sessionId,
                reason = reason,
            });
        }

        public void Dispose()
        {
            _cts?.Cancel();
            _ws?.Dispose();
        }
    }
}
