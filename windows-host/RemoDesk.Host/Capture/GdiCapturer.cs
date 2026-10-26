using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace RemoDesk.Host.Capture
{
    public class GdiCapturer : IScreenCapturer
    {
        private int _width;
        private int _height;
        private int _quality;
        private int _monitorIndex = 0;
        private ImageCodecInfo? _jpegEncoder;
        private EncoderParameters _encoderParams;

        public int ScreenWidth => _width;
        public int ScreenHeight => _height;
        public int MonitorCount => Screen.AllScreens.Length;
        public int CurrentMonitor => _monitorIndex;

        public GdiCapturer(int quality = 75)
        {
            _quality = quality;
            _width = Screen.PrimaryScreen?.Bounds.Width ?? 1920;
            _height = Screen.PrimaryScreen?.Bounds.Height ?? 1080;

            _jpegEncoder = GetEncoder(ImageFormat.Jpeg);
            _encoderParams = new EncoderParameters(1);
            _encoderParams.Param[0] = new EncoderParameter(Encoder.Quality, (long)quality);
        }

        public void SetQuality(int quality)
        {
            _quality = Math.Clamp(quality, 20, 100);
            _encoderParams.Param[0] = new EncoderParameter(Encoder.Quality, (long)_quality);
        }

        public void SetMonitor(int monitorIndex)
        {
            if (monitorIndex >= 0 && monitorIndex < Screen.AllScreens.Length && monitorIndex != _monitorIndex)
            {
                _monitorIndex = monitorIndex;
                Reinitialize();
            }
        }

        public void Reinitialize()
        {
            Initialize();
        }

        public bool Initialize()
        {
            var screens = Screen.AllScreens;
            if (_monitorIndex >= screens.Length) _monitorIndex = 0;
            var targetScreen = screens.Length > _monitorIndex ? screens[_monitorIndex] : Screen.PrimaryScreen;
            _width = targetScreen?.Bounds.Width ?? 1920;
            _height = targetScreen?.Bounds.Height ?? 1080;
            return true;
        }

        public CapturedFrame? CaptureFrame()
        {
            try
            {
                var screens = Screen.AllScreens;
                if (_monitorIndex >= screens.Length) _monitorIndex = 0;
                var targetScreen = screens.Length > _monitorIndex ? screens[_monitorIndex] : Screen.PrimaryScreen;
                int screenX = targetScreen?.Bounds.X ?? 0;
                int screenY = targetScreen?.Bounds.Y ?? 0;

                var bmp = new Bitmap(_width, _height, PixelFormat.Format32bppRgb);
                using (var g = Graphics.FromImage(bmp))
                {
                    g.CopyFromScreen(screenX, screenY, 0, 0, new Size(_width, _height), CopyPixelOperation.SourceCopy);

                    // Draw cursor
                    DrawCursor(g);
                }

                // Compress to JPEG for high-performance low-latency frame transport
                byte[] compressed;
                using (var ms = new MemoryStream())
                {
                    if (_jpegEncoder != null)
                    {
                        bmp.Save(ms, _jpegEncoder, _encoderParams);
                    }
                    else
                    {
                        bmp.Save(ms, ImageFormat.Jpeg);
                    }
                    compressed = ms.ToArray();
                }

                return new CapturedFrame
                {
                    Bitmap = bmp,
                    CompressedBytes = compressed,
                    Width = _width,
                    Height = _height,
                    TimestampMs = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds(),
                };
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Screen capture error: {ex.Message}");
                return null;
            }
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct POINT
        {
            public int x;
            public int y;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct CURSORINFO
        {
            public int cbSize;
            public int flags;
            public IntPtr hCursor;
            public POINT ptScreenPos;
        }

        private const int CURSOR_SHOWING = 0x00000001;

        [DllImport("user32.dll")]
        private static extern bool GetCursorInfo(out CURSORINFO pci);

        [DllImport("user32.dll")]
        private static extern bool DrawIcon(IntPtr hDC, int X, int Y, IntPtr hIcon);

        private void DrawCursor(Graphics g)
        {
            try
            {
                var ci = new CURSORINFO { cbSize = Marshal.SizeOf(typeof(CURSORINFO)) };
                if (GetCursorInfo(out ci) && ci.flags == CURSOR_SHOWING)
                {
                    IntPtr hdc = g.GetHdc();
                    DrawIcon(hdc, ci.ptScreenPos.x, ci.ptScreenPos.y, ci.hCursor);
                    g.ReleaseHdc(hdc);
                }
            }
            catch
            {
                // Cursor drawing is best-effort
            }
        }

        private static ImageCodecInfo? GetEncoder(ImageFormat format)
        {
            var codecs = ImageCodecInfo.GetImageEncoders();
            foreach (var codec in codecs)
            {
                if (codec.FormatID == format.Guid)
                {
                    return codec;
                }
            }
            return null;
        }

        public void Dispose()
        {
            _encoderParams.Dispose();
        }
    }
}
