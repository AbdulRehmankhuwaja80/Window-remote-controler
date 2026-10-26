using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using SharpDX;
using SharpDX.Direct3D11;
using SharpDX.DXGI;
using Device = SharpDX.Direct3D11.Device;
using MapFlags = SharpDX.Direct3D11.MapFlags;

namespace RemoDesk.Host.Capture
{
    public class DesktopDuplicationCapturer : IScreenCapturer
    {
        private Device? _device;
        private OutputDuplication? _deskDupl;
        private Texture2D? _stagingTexture;
        private int _width;
        private int _height;
        private int _quality;
        private int _monitorIndex = 0;
        private int _monitorCount = 1;
        private ImageCodecInfo? _jpegEncoder;
        private EncoderParameters _encoderParams;

        public int ScreenWidth => _width;
        public int ScreenHeight => _height;
        public int MonitorCount => _monitorCount;
        public int CurrentMonitor => _monitorIndex;

        public DesktopDuplicationCapturer(int quality = 75)
        {
            _quality = quality;
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
            if (monitorIndex >= 0 && monitorIndex < _monitorCount && monitorIndex != _monitorIndex)
            {
                _monitorIndex = monitorIndex;
                Reinitialize();
            }
        }

        public void Reinitialize()
        {
            try
            {
                _stagingTexture?.Dispose();
                _stagingTexture = null;
                _deskDupl?.Dispose();
                _deskDupl = null;
                _device?.Dispose();
                _device = null;

                Initialize();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Capturer reinitialization error: {ex.Message}");
            }
        }

        public bool Initialize()
        {
            try
            {
                using var factory = new Factory1();
                using var adapter = factory.GetAdapter1(0);
                _device = new Device(adapter);

                _monitorCount = Math.Max(1, adapter.GetOutputCount());
                if (_monitorIndex >= _monitorCount)
                {
                    _monitorIndex = 0;
                }

                using var output = adapter.GetOutput(_monitorIndex);
                using var output1 = output.QueryInterface<Output1>();

                var bounds = output.Description.DesktopBounds;
                _width = bounds.Right - bounds.Left;
                _height = bounds.Bottom - bounds.Top;

                _deskDupl = output1.DuplicateOutput(_device);

                var textureDesc = new Texture2DDescription
                {
                    CpuAccessFlags = CpuAccessFlags.Read,
                    BindFlags = BindFlags.None,
                    Format = Format.B8G8R8A8_UNorm,
                    Width = _width,
                    Height = _height,
                    OptionFlags = ResourceOptionFlags.None,
                    MipLevels = 1,
                    ArraySize = 1,
                    SampleDescription = { Count = 1, Quality = 0 },
                    Usage = ResourceUsage.Staging
                };

                _stagingTexture = new Texture2D(_device, textureDesc);
                return true;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"DXGI Duplication init failed (falling back to GDI): {ex.Message}");
                return false;
            }
        }

        public CapturedFrame? CaptureFrame()
        {
            if (_deskDupl == null || _device == null || _stagingTexture == null)
            {
                return null;
            }

            SharpDX.DXGI.Resource? desktopResource = null;
            try
            {
                var result = _deskDupl.TryAcquireNextFrame(100, out var frameInfo, out desktopResource);
                if (result.Failure || desktopResource == null)
                {
                    return null;
                }

                using var desktopTexture = desktopResource.QueryInterface<Texture2D>();
                _device.ImmediateContext.CopyResource(desktopTexture, _stagingTexture);

                var dataBox = _device.ImmediateContext.MapSubresource(_stagingTexture, 0, MapMode.Read, MapFlags.None);
                
                var bmp = new Bitmap(_width, _height, PixelFormat.Format32bppRgb);
                var boundsRect = new Rectangle(0, 0, _width, _height);
                var mapDest = bmp.LockBits(boundsRect, ImageLockMode.WriteOnly, bmp.PixelFormat);

                // Copy line-by-line handling pitch
                IntPtr sourcePtr = dataBox.DataPointer;
                IntPtr destPtr = mapDest.Scan0;
                for (int y = 0; y < _height; y++)
                {
                    Utilities.CopyMemory(destPtr, sourcePtr, _width * 4);
                    sourcePtr = IntPtr.Add(sourcePtr, dataBox.RowPitch);
                    destPtr = IntPtr.Add(destPtr, mapDest.Stride);
                }

                bmp.UnlockBits(mapDest);
                _device.ImmediateContext.UnmapSubresource(_stagingTexture, 0);

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
            catch (SharpDXException sEx)
            {
                if (sEx.ResultCode == SharpDX.DXGI.ResultCode.WaitTimeout)
                {
                    // No frame update in 100ms, normal
                    return null;
                }
                return null;
            }
            catch (Exception)
            {
                return null;
            }
            finally
            {
                desktopResource?.Dispose();
                try
                {
                    _deskDupl.ReleaseFrame();
                }
                catch { }
            }
        }

        private static ImageCodecInfo? GetEncoder(ImageFormat format)
        {
            var codecs = ImageCodecInfo.GetImageEncoders();
            foreach (var codec in codecs)
            {
                if (codec.FormatID == format.Guid) return codec;
            }
            return null;
        }

        public void Dispose()
        {
            _encoderParams.Dispose();
            _stagingTexture?.Dispose();
            _deskDupl?.Dispose();
            _device?.Dispose();
        }
    }
}
