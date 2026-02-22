#!/usr/bin/env python3
"""
System check script to verify all dependencies and hardware before running.

Usage:
    python check_system.py
"""
import sys
import subprocess
import importlib.util

def check_python_version():
    """Check Python version."""
    print("🔍 Checking Python version...")
    version = sys.version_info
    
    if version.major != 3:
        print(f"   ❌ Python 3.x required, found {version.major}.{version.minor}")
        return False
    
    if version.minor < 8:
        print(f"   ⚠️  Python 3.8+ recommended, found {version.major}.{version.minor}")
    else:
        print(f"   ✓ Python {version.major}.{version.minor}.{version.micro}")
    
    return True


def check_package(package_name, import_name=None):
    """Check if a Python package is installed."""
    if import_name is None:
        import_name = package_name
    
    spec = importlib.util.find_spec(import_name)
    if spec is None:
        print(f"   ❌ {package_name} not installed")
        return False
    else:
        try:
            module = importlib.import_module(import_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"   ✓ {package_name} ({version})")
        except:
            print(f"   ✓ {package_name} (version unknown)")
        return True


def check_dependencies():
    """Check all required dependencies."""
    print("\n🔍 Checking Python packages...")
    
    required = [
        ("ultralytics", "ultralytics"),
        ("opencv-python", "cv2"),
        ("numpy", "numpy"),
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("websockets", "websockets"),
        ("pydantic", "pydantic"),
    ]
    
    all_ok = True
    for package_name, import_name in required:
        if not check_package(package_name, import_name):
            all_ok = False
    
    if not all_ok:
        print("\n❌ Missing packages. Install with:")
        print("   pip install -r requirements.txt")
    
    return all_ok


def check_camera():
    """Check if camera is accessible."""
    print("\n🔍 Checking camera access...")
    
    try:
        import cv2
        
        # Try to open camera
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("   ❌ Camera 0 not accessible")
            print("   Try different camera index: PC_CAMERA_INDEX=1")
            return False
        
        # Try to read frame
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            print("   ❌ Cannot read from camera")
            return False
        
        h, w = frame.shape[:2]
        print(f"   ✓ Camera 0 accessible ({w}x{h})")
        return True
    
    except Exception as e:
        print(f"   ❌ Camera check failed: {e}")
        return False


def check_gpu():
    """Check if CUDA GPU is available."""
    print("\n🔍 Checking GPU availability...")
    
    try:
        import torch
        
        if torch.cuda.is_available():
            device_name = torch.cuda.get_device_name(0)
            print(f"   ✓ CUDA GPU available: {device_name}")
            print(f"   ℹ️  YOLOv8 will use GPU for inference")
            return True
        else:
            print("   ℹ️  No CUDA GPU detected")
            print("   ℹ️  YOLOv8 will use CPU (slower)")
            return False
    
    except Exception as e:
        print(f"   ℹ️  GPU check failed: {e}")
        print("   ℹ️  Will use CPU")
        return False


def check_model():
    """Check if YOLO model exists or can be downloaded."""
    print("\n🔍 Checking YOLO model...")
    
    try:
        from ultralytics import YOLO
        import os
        from pathlib import Path
        
        # Check cache directory
        cache_dir = Path.home() / ".cache" / "torch" / "hub" / "ultralytics"
        
        model_name = "yolov8n.pt"
        
        if (cache_dir / model_name).exists():
            print(f"   ✓ {model_name} found in cache")
            return True
        else:
            print(f"   ℹ️  {model_name} not in cache")
            print("   ℹ️  Will be downloaded on first run (~6MB)")
            return True
    
    except Exception as e:
        print(f"   ⚠️  Model check failed: {e}")
        return True  # Not critical, will download on run


def check_port():
    """Check if default port is available."""
    print("\n🔍 Checking port availability...")
    
    import socket
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 8000))
        sock.close()
        
        if result == 0:
            print("   ⚠️  Port 8000 is in use")
            print("   Use different port: python run.py --port 8080")
            return False
        else:
            print("   ✓ Port 8000 available")
            return True
    
    except Exception as e:
        print(f"   ⚠️  Port check failed: {e}")
        return True  # Not critical


def main():
    """Run all system checks."""
    print("=" * 60)
    print("People Counter - System Check")
    print("=" * 60)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Camera", check_camera),
        ("GPU", check_gpu),
        ("Model", check_model),
        ("Port", check_port),
    ]
    
    results = {}
    critical_failed = False
    
    for name, check_func in checks:
        try:
            results[name] = check_func()
            
            # Critical checks
            if name in ["Python Version", "Dependencies"] and not results[name]:
                critical_failed = True
        
        except Exception as e:
            print(f"   ❌ Check failed with error: {e}")
            results[name] = False
            if name in ["Python Version", "Dependencies"]:
                critical_failed = True
    
    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, result in results.items():
        status = "✓" if result else "❌"
        print(f"{status} {name}")
    
    print("=" * 60)
    
    if critical_failed:
        print("\n❌ Critical checks failed. Please fix the issues above.")
        print("\nTo install dependencies:")
        print("   pip install -r requirements.txt")
        return 1
    
    elif not results.get("Camera", False):
        print("\n⚠️  Camera not accessible. The application will start but CV worker will fail.")
        print("Check camera permissions and device index.")
        return 0
    
    else:
        print("\n✅ All checks passed! Ready to run.")
        print("\nStart the application:")
        print("   python run.py")
        print("   or")
        print("   uvicorn app.main:app --host 0.0.0.0 --port 8000")
        return 0


if __name__ == "__main__":
    sys.exit(main())
