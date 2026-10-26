using System;
using System.Drawing;

namespace RemoDesk.Host.Capture
{
    public class CapturedFrame : IDisposable
    {
        public Bitmap? Bitmap { get; set; }
        public byte[]? CompressedBytes { get; set; }
        public int Width { get; set; }
        public int Height { get; set; }
        public long TimestampMs { get; set; }

        public void Dispose()
        {
            Bitmap?.Dispose();
            Bitmap = null;
        }
    }

    public interface IScreenCapturer : IDisposable
    {
        bool Initialize();
        CapturedFrame? CaptureFrame();
        void SetQuality(int quality);
        void SetMonitor(int monitorIndex);
        void Reinitialize();
        int ScreenWidth { get; }
        int ScreenHeight { get; }
        int MonitorCount { get; }
        int CurrentMonitor { get; }
    }
}
