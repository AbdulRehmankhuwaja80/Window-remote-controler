using System;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

namespace RemoDesk.Host.Input
{
    public class WindowsInputInjector : IInputInjector
    {
        private static readonly int InputSize = Marshal.SizeOf(typeof(NativeMethods.INPUT));

        public void MoveMouseAbsolute(double normalizedX, double normalizedY)
        {
            normalizedX = Math.Clamp(normalizedX, 0.0, 1.0);
            normalizedY = Math.Clamp(normalizedY, 0.0, 1.0);

            int x = (int)(normalizedX * 65535.0);
            int y = (int)(normalizedY * 65535.0);

            var input = new NativeMethods.INPUT
            {
                type = NativeMethods.INPUT_MOUSE,
                u = new NativeMethods.InputUnion
                {
                    mi = new NativeMethods.MOUSEINPUT
                    {
                        dx = x,
                        dy = y,
                        dwFlags = NativeMethods.MOUSEEVENTF_MOVE |
                                  NativeMethods.MOUSEEVENTF_ABSOLUTE |
                                  NativeMethods.MOUSEEVENTF_VIRTUALDESK,
                        time = 0,
                    }
                }
            };

            NativeMethods.SendInput(1, new[] { input }, InputSize);
        }

        public void MoveMouseDelta(int dx, int dy)
        {
            var input = new NativeMethods.INPUT
            {
                type = NativeMethods.INPUT_MOUSE,
                u = new NativeMethods.InputUnion
                {
                    mi = new NativeMethods.MOUSEINPUT
                    {
                        dx = dx,
                        dy = dy,
                        dwFlags = NativeMethods.MOUSEEVENTF_MOVE,
                        time = 0,
                    }
                }
            };

            NativeMethods.SendInput(1, new[] { input }, InputSize);
        }

        public void MouseButtonDown(MouseButton button)
        {
            uint flag = button switch
            {
                MouseButton.Left => NativeMethods.MOUSEEVENTF_LEFTDOWN,
                MouseButton.Right => NativeMethods.MOUSEEVENTF_RIGHTDOWN,
                MouseButton.Middle => NativeMethods.MOUSEEVENTF_MIDDLEDOWN,
                _ => 0
            };

            if (flag == 0) return;

            var input = new NativeMethods.INPUT
            {
                type = NativeMethods.INPUT_MOUSE,
                u = new NativeMethods.InputUnion
                {
                    mi = new NativeMethods.MOUSEINPUT { dwFlags = flag }
                }
            };

            NativeMethods.SendInput(1, new[] { input }, InputSize);
        }

        public void MouseButtonUp(MouseButton button)
        {
            uint flag = button switch
            {
                MouseButton.Left => NativeMethods.MOUSEEVENTF_LEFTUP,
                MouseButton.Right => NativeMethods.MOUSEEVENTF_RIGHTUP,
                MouseButton.Middle => NativeMethods.MOUSEEVENTF_MIDDLEUP,
                _ => 0
            };

            if (flag == 0) return;

            var input = new NativeMethods.INPUT
            {
                type = NativeMethods.INPUT_MOUSE,
                u = new NativeMethods.InputUnion
                {
                    mi = new NativeMethods.MOUSEINPUT { dwFlags = flag }
                }
            };

            NativeMethods.SendInput(1, new[] { input }, InputSize);
        }

        public void MouseButtonClick(MouseButton button)
        {
            MouseButtonDown(button);
            Thread.Sleep(15);
            MouseButtonUp(button);
        }

        public void MouseDoubleClick(MouseButton button)
        {
            MouseButtonClick(button);
            Thread.Sleep(40);
            MouseButtonClick(button);
        }

        public void MouseScroll(int deltaX, int deltaY)
        {
            if (deltaY != 0)
            {
                var inputY = new NativeMethods.INPUT
                {
                    type = NativeMethods.INPUT_MOUSE,
                    u = new NativeMethods.InputUnion
                    {
                        mi = new NativeMethods.MOUSEINPUT
                        {
                            dwFlags = NativeMethods.MOUSEEVENTF_WHEEL,
                            mouseData = (uint)deltaY,
                        }
                    }
                };
                NativeMethods.SendInput(1, new[] { inputY }, InputSize);
            }

            if (deltaX != 0)
            {
                var inputX = new NativeMethods.INPUT
                {
                    type = NativeMethods.INPUT_MOUSE,
                    u = new NativeMethods.InputUnion
                    {
                        mi = new NativeMethods.MOUSEINPUT
                        {
                            dwFlags = NativeMethods.MOUSEEVENTF_HWHEEL,
                            mouseData = (uint)deltaX,
                        }
                    }
                };
                NativeMethods.SendInput(1, new[] { inputX }, InputSize);
            }
        }

        public void KeyDown(ushort virtualKey, bool isExtended = false)
        {
            uint flags = isExtended ? NativeMethods.KEYEVENTF_EXTENDEDKEY : 0;
            var input = new NativeMethods.INPUT
            {
                type = NativeMethods.INPUT_KEYBOARD,
                u = new NativeMethods.InputUnion
                {
                    ki = new NativeMethods.KEYBDINPUT
                    {
                        wVk = virtualKey,
                        wScan = (ushort)NativeMethods.MapVirtualKey(virtualKey, 0),
                        dwFlags = flags,
                    }
                }
            };
            NativeMethods.SendInput(1, new[] { input }, InputSize);
        }

        public void KeyUp(ushort virtualKey, bool isExtended = false)
        {
            uint flags = NativeMethods.KEYEVENTF_KEYUP | (isExtended ? NativeMethods.KEYEVENTF_EXTENDEDKEY : 0);
            var input = new NativeMethods.INPUT
            {
                type = NativeMethods.INPUT_KEYBOARD,
                u = new NativeMethods.InputUnion
                {
                    ki = new NativeMethods.KEYBDINPUT
                    {
                        wVk = virtualKey,
                        wScan = (ushort)NativeMethods.MapVirtualKey(virtualKey, 0),
                        dwFlags = flags,
                    }
                }
            };
            NativeMethods.SendInput(1, new[] { input }, InputSize);
        }

        public void SendUnicodeText(string text)
        {
            if (string.IsNullOrEmpty(text)) return;

            var inputs = new NativeMethods.INPUT[text.Length * 2];
            for (int i = 0; i < text.Length; i++)
            {
                char c = text[i];
                // Key down
                inputs[i * 2] = new NativeMethods.INPUT
                {
                    type = NativeMethods.INPUT_KEYBOARD,
                    u = new NativeMethods.InputUnion
                    {
                        ki = new NativeMethods.KEYBDINPUT
                        {
                            wVk = 0,
                            wScan = c,
                            dwFlags = NativeMethods.KEYEVENTF_UNICODE,
                        }
                    }
                };
                // Key up
                inputs[i * 2 + 1] = new NativeMethods.INPUT
                {
                    type = NativeMethods.INPUT_KEYBOARD,
                    u = new NativeMethods.InputUnion
                    {
                        ki = new NativeMethods.KEYBDINPUT
                        {
                            wVk = 0,
                            wScan = c,
                            dwFlags = NativeMethods.KEYEVENTF_UNICODE | NativeMethods.KEYEVENTF_KEYUP,
                        }
                    }
                };
            }

            NativeMethods.SendInput((uint)inputs.Length, inputs, InputSize);
        }

        public void SetClipboard(string text)
        {
            var thread = new Thread(() =>
            {
                try
                {
                    Clipboard.SetText(text);
                }
                catch { }
            });
            thread.SetApartmentState(ApartmentState.STA);
            thread.Start();
            thread.Join(500);
        }

        public string GetClipboard()
        {
            string result = string.Empty;
            var thread = new Thread(() =>
            {
                try
                {
                    if (Clipboard.ContainsText())
                    {
                        result = Clipboard.GetText();
                    }
                }
                catch { }
            });
            thread.SetApartmentState(ApartmentState.STA);
            thread.Start();
            thread.Join(500);
            return result;
        }
    }
}
