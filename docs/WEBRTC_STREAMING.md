# RemoDesk: WebRTC Low-Latency Streaming & Transport Deep Dive

## 1. Streaming Architecture Overview

RemoDesk uses standard **WebRTC (Web Real-Time Communication)** protocols to deliver low-latency screen streaming and sub-millisecond input control across different networks.

```
+--------------------------------------------------------------------------------+
|                             Windows Laptop Host                                |
|                                                                                |
|  [Desktop Duplication API / GDI]                                               |
|             |                                                                  |
|             v (BGRA Raw Frames @ 30-60 FPS)                                    |
|  [H.264 / VP8 Video Encoder]                                                   |
|             |                                                                  |
|             v (RTP Packetization)                                              |
|      +---------------+       +---------------------------------------------+   |
|      |  Video Track  |       | DataChannel ('remodesk-control')            |   |
|      +---------------+       +---------------------------------------------+   |
+--------------|--------------------------------------^--------------------------+
               | (DTLS-SRTP Video Media)              | (DTLS-SCTP Input Events)
               v                                      |
       =======================================================
       Internet / Disparate Networks (NAT / Firewalls / LTE)
       =======================================================
               |                                      ^
               v                                      |
+--------------|--------------------------------------|--------------------------+
|      +---------------+       +---------------------------------------------+   |
|      | Video Receiver|       | DataChannel ('remodesk-control')            |   |
|      +---------------+       +---------------------------------------------+   |
|             | (H.264 / VP8)                         ^                          |
|             v                                       |                          |
|  [Hardware Video Decoder]               [Touch & Gesture Interpreter]          |
|             |                                       |                          |
|             v                                       v                          |
|  [SurfaceViewRenderer]                  [Touchpad, Keys, Clipboard Sync]       |
|                                                                                |
|                                Android Phone Client                            |
+--------------------------------------------------------------------------------+
```

---

## 2. Low-Latency Media Pipeline

### A. Screen Capture
- **Primary Engine**: Windows Desktop Duplication API (DXGI 1.2+). Zero-copy GPU texture duplication from desktop output surface.
- **Fallback Engine**: Win32 GDI `BitBlt` with Per-Monitor DPI scaling and hardware cursor overlay rendering.

### B. Video Encoding & Codec Negotiation
- **Codecs**: H.264 Constrained Baseline Profile (CBP) / High Profile, with software VP8 fallback.
- **Bitrate Range**:
  - Wi-Fi: 2.5 Mbps – 6.0 Mbps @ 1080p 60 FPS
  - Cellular 4G/5G: 800 kbps – 2.0 Mbps @ 720p 30 FPS
  - Degraded Network: 350 kbps @ 480p 15 FPS

---

## 3. WebRTC DataChannel Input Transport

Control events are transmitted over an ordered, reliable SCTP DataChannel named `remodesk-control`.

### Message Payload Types

#### 1. Mouse Move (Absolute Normalized)
Sent when the user touches or drags on the screen:
```json
{
  "type": "mouse_move",
  "x": 0.5234,
  "y": 0.4129
}
```
*Windows Host maps coordinates to virtual screen space via:*
$$\text{virtualX} = \text{round}(x \times 65535)$$
$$\text{virtualY} = \text{round}(y \times 65535)$$

#### 2. Mouse Delta (Touchpad Trackpad Mode)
Sent when the user glides a finger on the virtual touchpad surface:
```json
{
  "type": "mouse_delta",
  "dx": -4,
  "dy": 12
}
```

#### 3. Mouse Buttons
```json
{
  "type": "mouse_button",
  "button": "left",
  "action": "click"
}
```
Supported buttons: `left`, `right`, `middle`.
Supported actions: `down`, `up`, `click`, `double_click`.

#### 4. Mouse Scroll Wheel
```json
{
  "type": "mouse_scroll",
  "dx": 0,
  "dy": -120
}
```

#### 5. Keystroke & Modifier Keys
```json
{
  "type": "key_event",
  "vk": 91,
  "action": "down",
  "extended": true
}
```

#### 6. Unicode Text Typing
```json
{
  "type": "text_input",
  "text": "Antigravity Remote Desktop"
}
```

---

## 4. NAT Traversal & Coturn Relay

When the Android client and Windows laptop reside on different networks (e.g. cellular mobile data vs home broadband Wi-Fi), direct P2P connectivity may be obstructed by symmetric NATs.

RemoDesk resolves this using **RFC 5766 TURN relays**:
1. Cloud gateway generates short-lived HMAC-SHA1 credentials via `/api/sessions/ice-servers`:
   - `username`: `<expiry_timestamp>:<user_id>`
   - `password`: `Base64(HMAC-SHA1(turn_secret, username))`
2. Peers attempt STUN hole punching first.
3. If hole punching fails after 500ms, WebRTC automatically switches to the TURN relay over UDP or TCP port 3478/5349.
