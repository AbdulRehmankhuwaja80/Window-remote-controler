using System;
using Newtonsoft.Json.Linq;
using RemoDesk.Host.Input;

namespace RemoDesk.Host.WebRtc
{
    public class DataChannelProtocol
    {
        private readonly IInputInjector _inputInjector;
        private readonly Func<bool> _isControlAllowed;
        public event Action<string>? OnClipboardReceived;
        public event Action<string>? OnSendMessage;

        public DataChannelProtocol(IInputInjector inputInjector, Func<bool> isControlAllowed)
        {
            _inputInjector = inputInjector;
            _isControlAllowed = isControlAllowed;
        }

        public void HandleMessage(string messageJson)
        {
            if (string.IsNullOrWhiteSpace(messageJson)) return;

            try
            {
                var jObj = JObject.Parse(messageJson);
                string type = jObj.Value<string>("type") ?? string.Empty;

                // Ping / Pong for measuring network latency
                if (type == "ping")
                {
                    long clientTime = jObj.Value<long>("timestamp");
                    var pong = new JObject
                    {
                        ["type"] = "pong",
                        ["client_time"] = clientTime,
                        ["host_time"] = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
                    };
                    OnSendMessage?.Invoke(pong.ToString());
                    return;
                }

                // Check if host has temporarily paused remote control
                if (!_isControlAllowed())
                {
                    return;
                }

                switch (type)
                {
                    case "mouse_move":
                        double x = jObj.Value<double>("x");
                        double y = jObj.Value<double>("y");
                        _inputInjector.MoveMouseAbsolute(x, y);
                        break;

                    case "mouse_delta":
                        int dx = jObj.Value<int>("dx");
                        int dy = jObj.Value<int>("dy");
                        _inputInjector.MoveMouseDelta(dx, dy);
                        break;

                    case "mouse_button":
                        string btnStr = jObj.Value<string>("button") ?? "left";
                        string action = jObj.Value<string>("action") ?? "click";
                        var button = btnStr.ToLower() switch
                        {
                            "right" => MouseButton.Right,
                            "middle" => MouseButton.Middle,
                            _ => MouseButton.Left,
                        };

                        if (action == "down") _inputInjector.MouseButtonDown(button);
                        else if (action == "up") _inputInjector.MouseButtonUp(button);
                        else if (action == "double_click") _inputInjector.MouseDoubleClick(button);
                        else _inputInjector.MouseButtonClick(button);
                        break;

                    case "mouse_scroll":
                        int sX = jObj.Value<int>("dx");
                        int sY = jObj.Value<int>("dy");
                        _inputInjector.MouseScroll(sX, sY);
                        break;

                    case "key_event":
                        ushort vk = jObj.Value<ushort>("vk");
                        string keyAction = jObj.Value<string>("action") ?? "down";
                        bool isExt = jObj.Value<bool>("extended");
                        if (keyAction == "down") _inputInjector.KeyDown(vk, isExt);
                        else if (keyAction == "up") _inputInjector.KeyUp(vk, isExt);
                        break;

                    case "text_input":
                        string text = jObj.Value<string>("text") ?? string.Empty;
                        _inputInjector.SendUnicodeText(text);
                        break;

                    case "clipboard_sync":
                        string clipText = jObj.Value<string>("content") ?? string.Empty;
                        _inputInjector.SetClipboard(clipText);
                        OnClipboardReceived?.Invoke(clipText);
                        break;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error processing input event: {ex.Message}");
            }
        }
    }
}
