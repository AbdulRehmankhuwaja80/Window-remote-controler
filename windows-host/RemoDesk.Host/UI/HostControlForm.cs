using System;
using System.Drawing;
using System.Windows.Forms;
using RemoDesk.Host.Security;
using RemoDesk.Host.Signaling;

namespace RemoDesk.Host.UI
{
    public class HostControlForm : Form
    {
        private readonly HostSettings _settings;
        private readonly SignalingClient _signaling;
        private readonly SessionAuthorizer _authorizer;

        private Label _lblStatus = null!;
        private Label _lblDeviceName = null!;
        private Label _lblSessionInfo = null!;
        private Button _btnDisconnect = null!;
        private CheckBox _chkPauseControl = null!;
        private CheckBox _chkStartWithWindows = null!;
        private NotifyIcon _trayIcon = null!;

        public event Action? OnManualDisconnectRequested;

        public HostControlForm(HostSettings settings, SignalingClient signaling, SessionAuthorizer authorizer)
        {
            _settings = settings;
            _signaling = signaling;
            _authorizer = authorizer;

            InitializeComponent();
            UpdateUiState();

            _signaling.OnConnectionStateChanged += (connected) =>
            {
                if (InvokeRequired)
                {
                    Invoke(new Action(() => UpdateConnectionStatus(connected)));
                }
                else
                {
                    UpdateConnectionStatus(connected);
                }
            };
        }

        private void InitializeComponent()
        {
            Text = "RemoDesk Host — Windows Agent";
            Size = new Size(520, 480);
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(15, 23, 42); // Dark navy
            ForeColor = Color.White;
            Font = new Font("Segoe UI", 10);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;

            // Header Banner
            var pnlHeader = new Panel
            {
                Dock = DockStyle.Top,
                Height = 70,
                BackColor = Color.FromArgb(30, 41, 59),
            };

            var lblTitle = new Label
            {
                Text = "RemoDesk Remote Host",
                Font = new Font("Segoe UI", 14, FontStyle.Bold),
                ForeColor = Color.FromArgb(96, 165, 250), // Electric blue accent
                Location = new Point(20, 12),
                AutoSize = true,
            };

            _lblDeviceName = new Label
            {
                Text = $"Device: {_settings.DeviceName} ({_settings.DeviceId[..Math.Min(8, _settings.DeviceId.Length)]}...)",
                Font = new Font("Segoe UI", 9),
                ForeColor = Color.FromArgb(148, 163, 184),
                Location = new Point(22, 40),
                AutoSize = true,
            };

            pnlHeader.Controls.Add(lblTitle);
            pnlHeader.Controls.Add(_lblDeviceName);
            Controls.Add(pnlHeader);

            // Status Card
            var grpStatus = new GroupBox
            {
                Text = "Connection & Status",
                ForeColor = Color.FromArgb(203, 213, 225),
                Location = new Point(20, 90),
                Size = new Size(465, 120),
            };

            _lblStatus = new Label
            {
                Text = "● Status: Connecting to gateway...",
                ForeColor = Color.Gold,
                Font = new Font("Segoe UI", 10, FontStyle.Bold),
                Location = new Point(20, 30),
                AutoSize = true,
            };

            _lblSessionInfo = new Label
            {
                Text = "No active remote session.",
                ForeColor = Color.FromArgb(148, 163, 184),
                Location = new Point(20, 60),
                Size = new Size(420, 45),
            };

            grpStatus.Controls.Add(_lblStatus);
            grpStatus.Controls.Add(_lblSessionInfo);
            Controls.Add(grpStatus);

            // Security & Pairing Card
            var grpSecurity = new GroupBox
            {
                Text = "Security & Host Controls",
                ForeColor = Color.FromArgb(203, 213, 225),
                Location = new Point(20, 225),
                Size = new Size(465, 110),
            };

            _chkPauseControl = new CheckBox
            {
                Text = "Pause Remote Input (Block incoming mouse/keyboard)",
                Checked = _settings.RemoteControlPaused,
                ForeColor = Color.White,
                Location = new Point(20, 30),
                AutoSize = true,
            };
            _chkPauseControl.CheckedChanged += (s, e) =>
            {
                _authorizer.IsPaused = _chkPauseControl.Checked;
                UpdateUiState();
            };

            _chkStartWithWindows = new CheckBox
            {
                Text = "Start automatically when Windows boots",
                Checked = _settings.StartWithWindows,
                ForeColor = Color.White,
                Location = new Point(20, 65),
                AutoSize = true,
            };
            _chkStartWithWindows.CheckedChanged += (s, e) =>
            {
                _settings.SetAutoStart(_chkStartWithWindows.Checked);
            };

            grpSecurity.Controls.Add(_chkPauseControl);
            grpSecurity.Controls.Add(_chkStartWithWindows);
            Controls.Add(grpSecurity);

            // Disconnect Button
            _btnDisconnect = new Button
            {
                Text = "Terminate Active Session",
                BackColor = Color.FromArgb(220, 38, 38), // Red
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Segoe UI", 11, FontStyle.Bold),
                Location = new Point(20, 355),
                Size = new Size(465, 45),
                Enabled = false,
            };
            _btnDisconnect.FlatAppearance.BorderSize = 0;
            _btnDisconnect.Click += (s, e) =>
            {
                OnManualDisconnectRequested?.Invoke();
                SetSessionActive(false, null);
            };
            Controls.Add(_btnDisconnect);

            // Tray Icon
            _trayIcon = new NotifyIcon
            {
                Text = "RemoDesk Host",
                Icon = SystemIcons.Application,
                Visible = true,
            };

            var trayMenu = new ContextMenuStrip();
            trayMenu.Items.Add("Open RemoDesk Host", null, (s, e) => { Show(); WindowState = FormWindowState.Normal; });
            trayMenu.Items.Add(new ToolStripSeparator());
            trayMenu.Items.Add("Pause Remote Input", null, (s, e) =>
            {
                _chkPauseControl.Checked = !_chkPauseControl.Checked;
            });
            trayMenu.Items.Add("Terminate Session", null, (s, e) =>
            {
                OnManualDisconnectRequested?.Invoke();
                SetSessionActive(false, null);
            });
            trayMenu.Items.Add(new ToolStripSeparator());
            trayMenu.Items.Add("Exit", null, (s, e) =>
            {
                _trayIcon.Visible = false;
                Application.Exit();
            });

            _trayIcon.ContextMenuStrip = trayMenu;
            _trayIcon.DoubleClick += (s, e) => { Show(); WindowState = FormWindowState.Normal; };

            FormClosing += (s, e) =>
            {
                if (e.CloseReason == CloseReason.UserClosing)
                {
                    e.Cancel = true;
                    Hide();
                    _trayIcon.ShowBalloonTip(2000, "RemoDesk Host", "Running in background. Remote access remains active.", ToolTipIcon.Info);
                }
            };
        }

        public void UpdateConnectionStatus(bool connected)
        {
            if (connected)
            {
                _lblStatus.Text = "● Status: Online (Ready for remote connections)";
                _lblStatus.ForeColor = Color.FromArgb(34, 197, 94); // Emerald green
            }
            else
            {
                _lblStatus.Text = "● Status: Disconnected from cloud gateway";
                _lblStatus.ForeColor = Color.FromArgb(239, 68, 68); // Red
            }
        }

        public void SetSessionActive(bool active, string? clientInfo)
        {
            if (InvokeRequired)
            {
                Invoke(new Action(() => SetSessionActive(active, clientInfo)));
                return;
            }

            if (active)
            {
                _lblStatus.Text = "● Status: IN SESSION — Controlling Laptop";
                _lblStatus.ForeColor = Color.FromArgb(59, 130, 246); // Blue
                _lblSessionInfo.Text = $"Connected Device: {clientInfo ?? "Android Client"}\nStarted: {DateTime.Now:HH:mm:ss}";
                _btnDisconnect.Enabled = true;
                _trayIcon.ShowBalloonTip(3000, "RemoDesk Active Session", $"Remote control active from {clientInfo}", ToolTipIcon.Warning);
            }
            else
            {
                UpdateConnectionStatus(_signaling.IsConnected);
                _lblSessionInfo.Text = "No active remote session.";
                _btnDisconnect.Enabled = false;
            }
        }

        private void UpdateUiState()
        {
            _chkPauseControl.Checked = _authorizer.IsPaused;
            _chkStartWithWindows.Checked = _settings.StartWithWindows;
        }

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                _trayIcon?.Dispose();
            }
            base.Dispose(disposing);
        }
    }
}
