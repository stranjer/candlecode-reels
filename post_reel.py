#!/usr/bin/env python3
"""Upload an MP4 to a Facebook Page as a Reel (Graph API Reels Publishing).
Env: FB_PAGE_ID, FB_PAGE_TOKEN (secret), GRAPH_VERSION (default v25.0)
usage: python3 post_reel.py video.mp4 "caption text"
"""
import os, sys, time, requests

V = os.environ.get("GRAPH_VERSION", "v25.0")
PAGE = os.environ["FB_PAGE_ID"]
TOKEN = os.environ["FB_PAGE_TOKEN"]

def main(path, caption):
    size = os.path.getsize(path)
    r = requests.post(f"https://graph.facebook.com/{V}/{PAGE}/video_reels",
                      json={"upload_phase": "start", "access_token": TOKEN}, timeout=60)
    if r.status_code >= 400: print(r.text)
    r.raise_for_status(); vid = r.json()["video_id"]
    print("started upload, video_id", vid)
    with open(path, "rb") as f:
        r = requests.post(f"https://rupload.facebook.com/video-upload/{V}/{vid}",
                          headers={"Authorization": f"OAuth {TOKEN}", "offset": "0", "file_size": str(size)},
                          data=f, timeout=300)
    if r.status_code >= 400: print(r.text)
    r.raise_for_status(); print("uploaded", r.json())
    r = requests.post(f"https://graph.facebook.com/{V}/{PAGE}/video_reels",
                      data={"access_token": TOKEN, "video_id": vid, "upload_phase": "finish",
                            "video_state": "PUBLISHED", "description": caption}, timeout=60)
    if r.status_code >= 400: print(r.text)
    r.raise_for_status(); print("publish requested", r.json())
    for _ in range(20):
        time.sleep(15)
        s = requests.get(f"https://graph.facebook.com/{V}/{vid}", params={"fields": "status", "access_token": TOKEN}, timeout=30)
        if s.ok:
            st = s.json().get("status", {})
            print("status", st)
            if st.get("video_status") in ("ready", "error"): break
    print(f"REEL_ID={vid}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
