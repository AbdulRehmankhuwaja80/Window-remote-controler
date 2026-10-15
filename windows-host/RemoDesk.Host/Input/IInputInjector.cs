using System;

namespace RemoDesk.Host.Input
{
    public enum MouseButton
    {
        Left,
        Right,
        Middle
    }

    public interface IInputInjector
    {
        void MoveMouseAbsolute(double normalizedX, double normalizedY);
        void MoveMouseDelta(int dx, int dy);
        void MouseButtonDown(MouseButton button);
        void MouseButtonUp(MouseButton button);
        void MouseButtonClick(MouseButton button);
        void MouseDoubleClick(MouseButton button);
        void MouseScroll(int deltaX, int deltaY);
        void KeyDown(ushort virtualKey, bool isExtended = false);
        void KeyUp(ushort virtualKey, bool isExtended = false);
        void SendUnicodeText(string text);
        void SetClipboard(string text);
        string GetClipboard();
    }
}
