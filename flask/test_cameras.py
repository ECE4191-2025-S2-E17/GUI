#!/usr/bin/env python3
"""
Test script for multiple camera sources
"""

import cv2
import time

def test_camera_sources():
    """Test all available camera sources"""
    print("🎥 Testing Camera Sources")
    print("=" * 30)
    
    for i in range(5):  # Test camera indices 0-4
        print(f"Testing Camera {i}...", end=" ")
        cap = cv2.VideoCapture(i)
        
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                height, width = frame.shape[:2]
                print(f"✅ Working ({width}x{height})")
                
                # Save test image
                cv2.imwrite(f"test_camera_{i}.jpg", frame)
                print(f"   📸 Saved test_camera_{i}.jpg")
            else:
                print("❌ No frame")
        else:
            print("❌ Not available")
        
        cap.release()
        time.sleep(0.5)

if __name__ == "__main__":
    test_camera_sources()
    print("\n💡 Usage:")
    print("- Update camera.py source=X where X is working camera index")
    print("- Connect USB camera and re-run this test")
    print("- Use working camera index in your Flask app")
