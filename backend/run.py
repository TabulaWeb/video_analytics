#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Convenient launcher script for People Counter application.

Usage:
    python run.py                # Start with default settings
    python run.py --port 8080    # Custom port
    python run.py --reload       # Enable auto-reload (dev mode)
"""
import argparse
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    # Parse arguments FIRST, before importing settings
    parser = argparse.ArgumentParser(
        description="People Counter - Real-time person tracking and counting"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload (development mode)"
    )
    parser.add_argument(
        "--no-debug-window",
        action="store_true",
        help="Disable OpenCV debug window"
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=0,
        help="Camera index (default: 0)"
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="YOLO model name (default: yolov8n.pt)"
    )
    
    args = parser.parse_args()
    
    # Override environment variables BEFORE importing settings
    if args.no_debug_window:
        os.environ["PC_SHOW_DEBUG_WINDOW"] = "false"
    
    if args.camera != 0:
        os.environ["PC_CAMERA_INDEX"] = str(args.camera)
    
    if args.model != "yolov8n.pt":
        os.environ["PC_MODEL_NAME"] = args.model
    
    # NOW import settings after env vars are set
    from app.config import settings
    
    # Print startup info
    print("=" * 60)
    print("People Counter - Starting...")
    print("=" * 60)
    print("Host: {}:{}".format(args.host, args.port))
    print("Camera: {}".format(args.camera))
    print("Model: {}".format(args.model))
    print("Debug window: {}".format(not args.no_debug_window))
    print("Reload: {}".format(args.reload))
    print("=" * 60)
    print("\n🌐 Web interface will be available at:")
    print("   http://{}:{}".format(args.host, args.port))
    print("\n📊 API endpoints:")
    print("   http://{}:{}/api/stats/current".format(args.host, args.port))
    print("   http://{}:{}/api/events".format(args.host, args.port))
    print("\n⌨️  Press Ctrl+C to stop\n")
    
    # Import and run uvicorn
    try:
        import uvicorn
        
        # Don't use reload in production or when CV worker is running
        # Reload can cause issues with threading
        if args.reload:
            print("⚠️  Warning: --reload may cause issues with camera/threading")
            print("   Use only for development without camera testing\n")
        
        uvicorn.run(
            "app.main:app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            log_level="info"
        )
    
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down gracefully...")
    
    except Exception as e:
        print("\n❌ Error: {}".format(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
