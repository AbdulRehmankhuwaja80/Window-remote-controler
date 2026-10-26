using System;
using System.Collections.Generic;
using System.IO;
using Microsoft.Win32;
using Newtonsoft.Json;

namespace RemoDesk.Host
{
    public class HostSettings
    {
        public string ServerUrl { get; set; } = "http://127.0.0.1:8000";
        public string SignalingWsUrl { get; set; } = "ws://127.0.0.1:8000/ws/signaling";
        public string DeviceId { get; set; } = string.Empty;
        public string DeviceName { get; set; } = Environment.MachineName;
        public string AuthKey { get; set; } = string.Empty;
        public string UserEmail { get; set; } = string.Empty;
        public string UserToken { get; set; } = string.Empty;

        public bool RequireApprovalForNewSessions { get; set; } = true;
        public bool StartWithWindows { get; set; } = false;
        public bool RemoteControlPaused { get; set; } = false;
        public bool IsRemoteAccessEnabled { get; set; } = true;
        public int SelectedMonitorIndex { get; set; } = 0;
        public bool FirstTimeConsentApproved { get; set; } = false;

        public int TargetFps { get; set; } = 30;
        public int JpegQuality { get; set; } = 75;

        public List<string> AuthorizedFilePaths { get; set; } = new List<string>
        {
            Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Downloads"),
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "Desktop"),
        };

        private static readonly string SettingsFilePath = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "RemoDesk",
            "host_config.json"
        );

        public static HostSettings Load()
        {
            try
            {
                if (File.Exists(SettingsFilePath))
                {
                    string json = File.ReadAllText(SettingsFilePath);
                    return JsonConvert.DeserializeObject<HostSettings>(json) ?? new HostSettings();
                }
            }
            catch (Exception)
            {
                // Fallback to default
            }

            var fresh = new HostSettings();
            fresh.Save();
            return fresh;
        }

        public void Save()
        {
            try
            {
                string dir = Path.GetDirectoryName(SettingsFilePath)!;
                if (!Directory.Exists(dir))
                {
                    Directory.CreateDirectory(dir);
                }
                string json = JsonConvert.SerializeObject(this, Formatting.Indented);
                File.WriteAllText(SettingsFilePath, json);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to save settings: {ex.Message}");
            }
        }

        public void SetAutoStart(bool enable)
        {
            StartWithWindows = enable;
            Save();

            const string runKey = @"SOFTWARE\Microsoft\Windows\CurrentVersion\Run";
            using var key = Registry.CurrentUser.OpenSubKey(runKey, true);
            if (key == null) return;

            string appPath = Environment.ProcessPath ?? string.Empty;
            if (string.IsNullOrEmpty(appPath)) return;

            if (enable)
            {
                key.SetValue("RemoDeskHost", $"\"{appPath}\" --minimized");
            }
            else
            {
                key.DeleteValue("RemoDeskHost", false);
            }
        }
    }
}
