using System;
using System.Collections.Generic;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using Newtonsoft.Json.Linq;
using RemoDesk.Host.Capture;
using RemoDesk.Host.FileServer;
using RemoDesk.Host.Input;
using RemoDesk.Host.Security;
using RemoDesk.Host.Signaling;
using RemoDesk.Host.UI;
using RemoDesk.Host.WebRtc;
using SIPSorcery.Net;

namespace RemoDesk.Host
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            ApplicationConfiguration.Initialize();

            var settings = HostSettings.Load();
            var inputInjector = new WindowsInputInjector();
            var authorizer = new SessionAuthorizer(settings);
            var fileManager = new RemoteFileManager(settings.AuthorizedFilePaths);

            // Select Screen Capturer (DirectX 11 Duplication with GDI Fallback)
            IScreenCapturer capturer = new DesktopDuplicationCapturer(settings.JpegQuality);
            if (!capturer.Initialize())
            {
                Console.WriteLine("Falling back to GDI screen capture.");
                capturer = new GdiCapturer(settings.JpegQuality);
                capturer.Initialize();
            }

            if (settings.SelectedMonitorIndex > 0)
            {
                capturer.SetMonitor(settings.SelectedMonitorIndex);
            }

            var signaling = new SignalingClient(settings);
            var rtcManager = new WebRtcSessionManager(capturer, inputInjector, () => settings.IsRemoteAccessEnabled && !authorizer.IsPaused);

            // Ensure Device is registered with Cloud Gateway
            Task.Run(async () =>
            {
                await EnsureDeviceRegisteredAsync(settings);
                await signaling.StartAsync();
            });

            var mainForm = new HostControlForm(settings, signaling, authorizer);

            mainForm.OnMonitorSelectionChanged += (idx) =>
            {
                capturer.SetMonitor(idx);
            };

            mainForm.OnRemoteAccessToggled += async (enabled) =>
            {
                await UpdateRemoteAccessOnBackendAsync(settings, enabled);
            };

            var dataChannelProtocol = new DataChannelProtocol(inputInjector, () => settings.IsRemoteAccessEnabled && !authorizer.IsPaused);

            signaling.OnInputMessageReceived += (msgJson) =>
            {
                dataChannelProtocol.HandleMessage(msgJson);
            };

            signaling.OnFileMessageReceived += async (msgJson) =>
            {
                await HandleFileServerMessageAsync(msgJson, fileManager, signaling);
            };

            signaling.OnControlMessageReceived += async (msgJson) =>
            {
                await HandleControlMessageAsync(msgJson, rtcManager, capturer, signaling);
            };

            rtcManager.OnFrameDataReady += async (base64) =>
            {
                if (signaling.IsConnected && !string.IsNullOrEmpty(rtcManager.CurrentSessionId))
                {
                    await signaling.SendDesktopFrameAsync(base64);
                }
            };

            // Connect Signaling events to WebRTC Session Manager
            signaling.OnSessionRequested += async (sessionId, clientId, clientInfo) =>
            {
                if (!settings.IsRemoteAccessEnabled)
                {
                    await signaling.RejectSessionAsync(sessionId, clientId, "Remote access is disabled on this laptop.");
                    return;
                }

                if (authorizer.IsPaused)
                {
                    await signaling.RejectSessionAsync(sessionId, clientId, "Remote control is currently paused by host.");
                    return;
                }

                bool accepted = authorizer.PromptUserForSession(clientInfo, sessionId);
                if (accepted)
                {
                    await signaling.AcceptSessionAsync(sessionId, clientId);
                    mainForm.SetSessionActive(true, clientInfo);
                    rtcManager.StartStreaming(settings.TargetFps);
                }
                else
                {
                    await signaling.RejectSessionAsync(sessionId, clientId, "Host declined connection request.");
                }
            };

            signaling.OnOfferReceived += async (sessionId, sdpOffer) =>
            {
                try
                {
                    var iceServers = new List<RTCIceServer>
                    {
                        new RTCIceServer { urls = "stun:stun.l.google.com:19302" },
                        new RTCIceServer { urls = "stun:stun1.l.google.com:19302" },
                        new RTCIceServer { urls = "stun:stun2.l.google.com:19302" },
                    };

                    string answerSdp = await rtcManager.HandleOfferAsync(sessionId, sdpOffer, iceServers);
                    await signaling.SendSdpAnswerAsync(sessionId, answerSdp);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error answering SDP offer: {ex.Message}");
                }
            };

            signaling.OnCandidateReceived += (sessionId, candidate) =>
            {
                rtcManager.AddIceCandidate(candidate);
            };

            signaling.OnSessionTerminated += (sessionId, reason) =>
            {
                rtcManager.StopStreaming();
                mainForm.SetSessionActive(false, null);
            };

            rtcManager.OnIceCandidateGenerated += async (candidateJson) =>
            {
                if (!string.IsNullOrEmpty(rtcManager.CurrentSessionId))
                {
                    await signaling.SendIceCandidateAsync(rtcManager.CurrentSessionId, candidateJson);
                }
            };

            mainForm.OnManualDisconnectRequested += async () =>
            {
                if (!string.IsNullOrEmpty(rtcManager.CurrentSessionId))
                {
                    await signaling.TerminateSessionAsync(rtcManager.CurrentSessionId, "Host manually terminated session.");
                    rtcManager.StopStreaming();
                }
            };

            Application.Run(mainForm);
        }

        private static async Task HandleFileServerMessageAsync(string msgJson, RemoteFileManager fileManager, SignalingClient signaling)
        {
            try
            {
                var jObj = JObject.Parse(msgJson);
                string type = jObj.Value<string>("type") ?? string.Empty;
                string clientId = jObj.Value<string>("client_id") ?? string.Empty;

                switch (type)
                {
                    case "fs_list":
                        {
                            string path = jObj.Value<string>("path") ?? string.Empty;
                            try
                            {
                                var entries = fileManager.ListDirectory(path);
                                await signaling.SendMessageAsync(new
                                {
                                    type = "fs_list_response",
                                    client_id = clientId,
                                    path,
                                    entries,
                                });
                            }
                            catch (Exception ex)
                            {
                                await signaling.SendMessageAsync(new
                                {
                                    type = "fs_list_response",
                                    client_id = clientId,
                                    path,
                                    error = ex.Message,
                                });
                            }
                            break;
                        }

                    case "fs_read_chunk":
                        {
                            string path = jObj.Value<string>("path") ?? string.Empty;
                            long offset = jObj.Value<long>("offset");
                            int length = jObj.Value<int>("length");
                            if (length <= 0) length = 65536;

                            try
                            {
                                byte[] chunk = fileManager.ReadFileChunk(path, offset, length, out bool isEof, out string sha256);
                                string b64 = Convert.ToBase64String(chunk);
                                await signaling.SendMessageAsync(new
                                {
                                    type = "fs_read_chunk_response",
                                    client_id = clientId,
                                    path,
                                    offset,
                                    data = b64,
                                    is_eof = isEof,
                                    sha256,
                                });
                            }
                            catch (Exception ex)
                            {
                                await signaling.SendMessageAsync(new
                                {
                                    type = "fs_read_chunk_response",
                                    client_id = clientId,
                                    path,
                                    offset,
                                    error = ex.Message,
                                });
                            }
                            break;
                        }

                    case "fs_write_chunk":
                        {
                            string path = jObj.Value<string>("path") ?? string.Empty;
                            long offset = jObj.Value<long>("offset");
                            string b64 = jObj.Value<string>("data") ?? string.Empty;
                            bool isComplete = jObj.Value<bool>("is_complete");
                            bool overwrite = jObj.Value<bool>("overwrite");

                            try
                            {
                                if (offset == 0 && File.Exists(path) && !overwrite)
                                {
                                    await signaling.SendMessageAsync(new
                                    {
                                        type = "fs_write_chunk_response",
                                        client_id = clientId,
                                        path,
                                        error = "file_exists",
                                    });
                                    return;
                                }

                                byte[] data = Convert.FromBase64String(b64);
                                fileManager.WriteFileChunk(path, offset, data, isComplete);
                                await signaling.SendMessageAsync(new
                                {
                                    type = "fs_write_chunk_response",
                                    client_id = clientId,
                                    path,
                                    offset,
                                    success = true,
                                    is_complete = isComplete,
                                });
                            }
                            catch (Exception ex)
                            {
                                await signaling.SendMessageAsync(new
                                {
                                    type = "fs_write_chunk_response",
                                    client_id = clientId,
                                    path,
                                    offset,
                                    error = ex.Message,
                                });
                            }
                            break;
                        }

                    case "fs_delete":
                        {
                            string path = jObj.Value<string>("path") ?? string.Empty;
                            try
                            {
                                fileManager.DeleteFile(path);
                                await signaling.SendMessageAsync(new
                                {
                                    type = "fs_delete_response",
                                    client_id = clientId,
                                    path,
                                    success = true,
                                });
                            }
                            catch (Exception ex)
                            {
                                await signaling.SendMessageAsync(new
                                {
                                    type = "fs_delete_response",
                                    client_id = clientId,
                                    path,
                                    error = ex.Message,
                                });
                            }
                            break;
                        }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error handling file server message: {ex.Message}");
            }
        }

        private static async Task HandleControlMessageAsync(
            string msgJson,
            WebRtcSessionManager rtcManager,
            IScreenCapturer capturer,
            SignalingClient signaling)
        {
            try
            {
                var jObj = JObject.Parse(msgJson);
                string type = jObj.Value<string>("type") ?? string.Empty;

                if (type == "set_quality")
                {
                    int fps = jObj.Value<int?>("target_fps") ?? 30;
                    int quality = jObj.Value<int?>("jpeg_quality") ?? 75;
                    rtcManager.SetStreamingQuality(fps, quality);
                }
                else if (type == "select_monitor")
                {
                    int monitorIdx = jObj.Value<int>("monitor_index");
                    capturer.SetMonitor(monitorIdx);
                }
                else if (type == "get_monitors")
                {
                    var screens = Screen.AllScreens;
                    var list = new List<object>();
                    for (int i = 0; i < screens.Length; i++)
                    {
                        var s = screens[i];
                        list.Add(new
                        {
                            index = i,
                            name = $"Display {i + 1}",
                            width = s.Bounds.Width,
                            height = s.Bounds.Height,
                            primary = s.Primary,
                        });
                    }
                    await signaling.SendMessageAsync(new
                    {
                        type = "monitors_response",
                        monitors = list,
                    });
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error handling control message: {ex.Message}");
            }
        }

        private static async Task UpdateRemoteAccessOnBackendAsync(HostSettings settings, bool enabled)
        {
            if (string.IsNullOrEmpty(settings.DeviceId)) return;
            try
            {
                using var client = new HttpClient();
                client.BaseAddress = new Uri(settings.ServerUrl);
                if (!string.IsNullOrEmpty(settings.UserToken))
                {
                    client.DefaultRequestHeaders.Authorization =
                        new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", settings.UserToken);
                }

                var patchObj = new { is_remote_enabled = enabled };
                var content = new StringContent(
                    Newtonsoft.Json.JsonConvert.SerializeObject(patchObj),
                    Encoding.UTF8,
                    "application/json"
                );
                await client.PatchAsync($"/api/devices/{settings.DeviceId}", content);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Backend remote access update: {ex.Message}");
            }
        }

        private static async Task EnsureDeviceRegisteredAsync(HostSettings settings)
        {
            if (!string.IsNullOrEmpty(settings.DeviceId) && !string.IsNullOrEmpty(settings.AuthKey))
            {
                return;
            }

            try
            {
                using var client = new HttpClient();
                client.BaseAddress = new Uri(settings.ServerUrl);

                if (!string.IsNullOrEmpty(settings.UserToken))
                {
                    client.DefaultRequestHeaders.Authorization =
                        new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", settings.UserToken);
                }

                var payload = new
                {
                    device_name = settings.DeviceName,
                    hostname = Environment.MachineName,
                    os_info = Environment.OSVersion.VersionString,
                    hardware_id = Environment.MachineName + "-" + Environment.UserName,
                };

                string json = Newtonsoft.Json.JsonConvert.SerializeObject(payload);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var resp = await client.PostAsync("/api/devices/register-host", content);
                if (resp.IsSuccessStatusCode)
                {
                    string respJson = await resp.Content.ReadAsStringAsync();
                    var jObj = JObject.Parse(respJson);
                    settings.DeviceId = jObj["device"]?["id"]?.ToString() ?? Guid.NewGuid().ToString();
                    settings.AuthKey = jObj["auth_key"]?.ToString() ?? Guid.NewGuid().ToString("N");
                    settings.Save();
                    Console.WriteLine($"Registered device ID: {settings.DeviceId}");
                }
                else
                {
                    settings.DeviceId = Guid.NewGuid().ToString();
                    settings.AuthKey = Guid.NewGuid().ToString("N");
                    settings.Save();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Device auto-registration note: {ex.Message}");
                if (string.IsNullOrEmpty(settings.DeviceId))
                {
                    settings.DeviceId = Guid.NewGuid().ToString();
                    settings.AuthKey = Guid.NewGuid().ToString("N");
                    settings.Save();
                }
            }
        }
    }
}
