#!/usr/bin/env python3
"""
ESP32-CAM Network Discovery Tool
Searches for ESP32-CAM devices on the local network
"""

import requests
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

def get_local_ip_range():
    """Get the local network IP range"""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        
        # Extract network prefix (assumes /24 subnet)
        ip_parts = local_ip.split('.')
        network = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}"
        
        return network, local_ip
    except:
        return None, None

def test_esp32_at_ip(ip):
    """Test if ESP32 is accessible at given IP"""
    try:
        # Test root endpoint first
        response = requests.get(f"http://{ip}/", timeout=2)
        if response.status_code == 200 and len(response.text) > 100:
            # Check if it responds to stream endpoint 
            try:
                stream_response = requests.get(f"http://{ip}/stream", timeout=1, stream=True)
                has_stream = stream_response.status_code == 200
            except:
                has_stream = False
                
            return {
                'ip': ip,
                'reachable': True,
                'has_webpage': True,
                'has_stream': has_stream,
                'content_length': len(response.text)
            }
    except:
        pass
    
    return None

def scan_network():
    """Scan local network for ESP32 devices"""
    print("🔍 Scanning local network for ESP32-CAM devices...")
    
    network, local_ip = get_local_ip_range()
    if not network:
        print("❌ Could not determine local network range")
        return []
    
    print(f"📡 Local IP: {local_ip}")
    print(f"🌐 Scanning network: {network}.x")
    
    # Common ESP32 IPs to check first
    priority_ips = [
        "192.168.4.1",   # Default ESP32 AP mode
        "192.168.1.1",   # Common router/AP IP
        f"{network}.1",   # Router IP
        f"{network}.100", # Common device range
        f"{network}.101",
        f"{network}.102"
    ]
    
    found_devices = []
    
    # Check priority IPs first
    print("🎯 Checking priority IP addresses...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(test_esp32_at_ip, ip) for ip in priority_ips]
        for future in futures:
            result = future.result()
            if result:
                found_devices.append(result)
                print(f"✅ ESP32 found at {result['ip']} (stream: {result['has_stream']})")
    
    if found_devices:
        print(f"\n🎉 Found {len(found_devices)} ESP32 device(s)!")
        return found_devices
    
    # If no priority IPs worked, scan the full range
    print("🔍 Priority IPs failed, scanning full network range...")
    print("⏳ This may take a moment...")
    
    ip_range = [f"{network}.{i}" for i in range(1, 255)]
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(test_esp32_at_ip, ip) for ip in ip_range]
        for i, future in enumerate(futures):
            if i % 50 == 0:
                print(f"📊 Progress: {i}/254 IPs checked")
            result = future.result()
            if result:
                found_devices.append(result)
                print(f"✅ ESP32 found at {result['ip']} (stream: {result['has_stream']})")
    
    return found_devices

def main():
    """Main function"""
    print("=" * 60)
    print("ESP32-CAM Network Discovery Tool")
    print("=" * 60)
    
    devices = scan_network()
    
    print("\n" + "=" * 60)
    print("SCAN RESULTS")
    print("=" * 60)
    
    if devices:
        print(f"Found {len(devices)} ESP32 device(s):")
        print()
        for device in devices:
            print(f"🤖 ESP32 Device:")
            print(f"   IP Address: {device['ip']}")
            print(f"   Webpage: {'✅ Available' if device['has_webpage'] else '❌ Not available'}")
            print(f"   Video Stream: {'✅ Available' if device['has_stream'] else '❌ Not available'}")
            print(f"   Content Size: {device['content_length']} bytes")
            print()
            
        print("💡 Usage:")
        print("1. Update main.py with the correct ESP32 IP address")
        print("2. Make sure you're connected to the same network as the ESP32")
        print("3. If using AP mode, connect to the ESP32's WiFi network")
        
    else:
        print("❌ No ESP32 devices found on the network")
        print()
        print("🔧 Troubleshooting:")
        print("1. Make sure the ESP32 is powered on and connected to WiFi")
        print("2. Check if you're on the same network as the ESP32")
        print("3. If ESP32 is in AP mode, connect to its WiFi network first")
        print("4. Verify the ESP32 webserver code is running correctly")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
