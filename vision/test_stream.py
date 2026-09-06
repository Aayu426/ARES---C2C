"""Quick check that an ESP32-CAM (or any) MJPEG stream opens and delivers frames.

    python test_stream.py http://192.168.137.23:81/stream

Prints the resolution and FPS it manages, and pops a window (press q to close). If this
works, the vision service will work with the same --cam-url."""
from __future__ import annotations

import sys
import time

import cv2


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: python test_stream.py <stream-url>")
    url = sys.argv[1]
    print(f"opening {url} ...")
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        raise SystemExit("could NOT open the stream. Check the URL, the hotspot, and the firewall.")
    n, t0 = 0, time.time()
    ok, frame = cap.read()
    if not ok:
        raise SystemExit("opened, but no frame arrived. The CAM is up but not streaming (supply? ribbon?).")
    h, w = frame.shape[:2]
    print(f"streaming OK: {w}x{h}")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("frame dropped")
            continue
        n += 1
        if n % 30 == 0:
            print(f"{n / (time.time() - t0):.1f} fps")
        cv2.imshow("esp32-cam test (q to quit)", frame)
        if (cv2.waitKey(1) & 0xFF) == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
