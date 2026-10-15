using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using Newtonsoft.Json.Linq;
using RemoDesk.Host.Capture;
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

            // Select Screen Capturer (DirectX 11 Duplication with GDI Fallback)
            IScreenCapturer capturer = new DesktopDuplicationCapturer(settings.JpegQuality);
            if (!capturer.Initialize())
            {
                Console.WriteLine("Falling back to GDI screen capture.");
                capturer = new GdiCapturer(settings.JpegQuality);
                capturer.Initialize();
            }

            var signaling = new SignalingClient(settings);
            var rtcManager = new WebRtcSessionManager(capturer, inputInjector, () => !authorizer.IsPaused);

            // Ensure Device is registered with Cloud Gateway
            Task.Run(async () =>
            {
                await EnsureDeviceRegisteredAsync(settings);
                await signaling.StartAsync();
            });

            var mainForm = new HostControlForm(settings, signaling, authorizer);

            // Connect Signaling events to WebRTC Session Manager
            signaling.OnSessionRequested += async (sessionId, clientId, clientInfo) =>
            {
                bool accepted = authorizer.PromptUserForSession(clientInfo, sessionId);
                if (accepted)
                {
                    await signaling.AcceptSessionAsync(sessionId, clientId);
                    mainForm.SetSessionActive(true, clientInfo);
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

                // If user is already authenticated
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
                    // Generate local temporary standalone device ID if running in offline/local mock mode
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
