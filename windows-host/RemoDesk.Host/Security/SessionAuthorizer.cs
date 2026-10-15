using System;
using System.Windows.Forms;

namespace RemoDesk.Host.Security
{
    public class SessionAuthorizer
    {
        private readonly HostSettings _settings;

        public bool IsPaused
        {
            get => _settings.RemoteControlPaused;
            set
            {
                _settings.RemoteControlPaused = value;
                _settings.Save();
            }
        }

        public SessionAuthorizer(HostSettings settings)
        {
            _settings = settings;
        }

        public bool PromptUserForSession(string clientInfo, string sessionId)
        {
            if (!_settings.RequireApprovalForNewSessions)
            {
                return true;
            }

            bool authorized = false;

            // Prompt in a clean top-most dialog
            var thread = new System.Threading.Thread(() =>
            {
                var result = MessageBox.Show(
                    $"An incoming remote control request has been received from:\n\n" +
                    $"Device: {clientInfo}\n" +
                    $"Session ID: {sessionId}\n\n" +
                    $"Do you want to allow this device to view and control your laptop screen?",
                    "RemoDesk — Incoming Remote Access Request",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question,
                    MessageBoxDefaultButton.Button2,
                    MessageBoxOptions.DefaultDesktopOnly
                );

                authorized = (result == DialogResult.Yes);
            });

            thread.SetApartmentState(System.Threading.ApartmentState.STA);
            thread.Start();
            thread.Join(30000); // 30-second timeout

            return authorized;
        }
    }
}
