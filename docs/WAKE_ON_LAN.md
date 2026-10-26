# RemoDesk — Wake-on-LAN (WoL) Setup Guide

Wake-on-LAN allows you to remotely power on or resume your sleeping or hibernating Windows host laptop from anywhere before initiating a RemoDesk remote session.

---

## 1. How Wake-on-LAN Works

When a computer goes to Sleep (S3), Hibernate (S4), or Soft-Off (S5), the network adapter enters a low-power standby mode listening for a **Magic Packet**.
- **Magic Packet**: An Ethernet frame containing 6 bytes of `0xFF` followed by 16 repetitions of the network card's 48-bit MAC address.
- When detected by the network card hardware, the NIC asserts the PME (Power Management Event) line to trigger motherboard power sequencing.

---

## 2. Motherboard BIOS / UEFI Configuration

1. Restart your laptop and press the BIOS key during boot (**F2**, **F10**, **F12**, or **Del** depending on manufacturer: Dell, Lenovo, HP, ASUS).
2. Navigate to **Power Management**, **Advanced**, or **ACPI Configuration**:
   - Set **Wake on LAN (WoL)** or **Wake on PCIe/PCI Devices** to **Enabled**.
   - If present, set **ErP / EuP Ready** or **Deep Sleep** to **Disabled** (if enabled, it cuts standby power to the NIC in S4/S5 states).
   - Set **Network Boot** or **PXE ROM** to Enabled if your motherboard links NIC standby power to PXE.
3. Save changes (**F10**) and boot into Windows.

---

## 3. Windows Network Adapter Driver Settings

1. Press `Win + X` and select **Device Manager**.
2. Expand **Network adapters**, right-click your active Ethernet adapter (e.g. *Intel(R) Ethernet Controller* or *Realtek PCIe GbE*), and select **Properties**.
3. Go to the **Power Management** tab:
   - Check **"Allow this device to wake the computer"**.
   - Check **"Only allow a magic packet to wake the computer"** (crucial to prevent random wakes from network noise).
4. Go to the **Advanced** tab:
   - Set **"Wake on Magic Packet"** to **Enabled**.
   - Set **"Shutdown Wake-On-Lan"** to **Enabled** (if available).
   - Set **"Energy Efficient Ethernet"** / **"Green Ethernet"** to **Disabled** if experiencing intermittent dropouts.
5. Click **OK**.

> [!NOTE]
> **Wi-Fi (WoWLAN)**: Most laptops only support Wake-on-LAN via wired Ethernet. Wake-on-Wireless-LAN (WoWLAN) requires modern standby (S0ix) and specialized Intel/Qualcomm Wi-Fi drivers. For highest reliability, keep the laptop plugged into Ethernet.

---

## 4. Disabling Fast Startup

Windows Fast Startup (Hybrid Sleep) can prevent the NIC from listening to magic packets in full shutdown:
1. Open PowerShell or Command Prompt as Administrator.
2. Run:
   ```cmd
   powercfg -h off
   ```
   *(Or navigate to Control Panel -> Power Options -> "Choose what the power buttons do" -> Uncheck "Turn on fast startup")*.

---

## 5. Finding Your MAC and IP Address

On the host laptop, run:
```cmd
ipconfig /all
```
Note down:
- **Physical Address (MAC)**: e.g. `00-D8-61-3A-9F-2B`
- **IPv4 Address**: e.g. `192.168.1.150`
- **Default Gateway**: e.g. `192.168.1.1`

---

## 6. Waking Over the Internet (Wake-on-WAN)

To wake your laptop when away from home:
1. **Router Static DHCP / ARP Binding**:
   - Access your home router admin panel (`http://192.168.1.1`).
   - Assign a static local IP reservation for your laptop's MAC (e.g. `192.168.1.150`).
   - Add a static ARP binding mapping `192.168.1.150` to `00:D8:61:3A:9F:2B` so the router retains the MAC address even when the PC is powered off.
2. **Port Forwarding**:
   - Forward **UDP Port 9** (or Port 7) to your laptop's IP (`192.168.1.150`) or to the subnet broadcast (`192.168.1.255`).
3. **Dynamic DNS (DDNS)**:
   - Enable DDNS on your router (e.g., No-IP, DuckDNS) if your ISP provides a dynamic public IP.
4. **Sending the Magic Packet**:
   - Send the packet to `your-ddns-hostname:9` with your laptop's MAC address.

---

## 7. RemoDesk Sleep Prevention During Active Sessions

While connected, RemoDesk Host automatically invokes the Windows Win32 API:
```csharp
SetThreadExecutionState(EXECUTION_STATE.ES_CONTINUOUS | EXECUTION_STATE.ES_SYSTEM_REQUIRED | EXECUTION_STATE.ES_DISPLAY_REQUIRED);
```
This guarantees your laptop will **never fall asleep** while you are actively streaming or transferring files. When the session terminates, the normal power saving policy is automatically restored.
