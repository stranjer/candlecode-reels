#!/usr/bin/env python3
"""Upload an MP4 to a Facebook Page as a Reel (Graph API Reels Publishing).
Env: FB_PAGE_ID, FB_PAGE_TOKEN (secret: a Page token, or a long-lived User token of a Page admin), GRAPH_VERSION
usage: python3 post_reel.py video.mp4 "caption text"
"""
import os, sys, time, requests

V = os.environ.get("GRAPH_VERSION", "v25.0")
PAGE = os.environ["FB_PAGE_ID"]
G = f"https://graph.facebook.com/{V}"

def page_token(tok):
    me = requests.get(f"{G}/me", params={"fields": "id,name", "access_token": tok}, timeout=30)
    if not me.ok:
        print("Token check failed:", me.text); me.raise_for_status()
    me = me.json()
    if me.get("id") == PAGE:
        print(f"Token OK: Page token for '{me.get('name')}'")
        return tok
    print(f"Token is a USER token (for '{me.get('name')}'), looking up the Page token...")
    r = requests.get(f"{G}/me/accounts", params={"fields": "id,name,access_token,tasks", "limit": 100, "access_token": tok}, timeout=30)
    if not r.ok: print(r.text); r.raise_for_status()
    for p in r.json().get("data", []):
        if p.get("id") == PAGE:
            print(f"Found Page '{p.get('name')}', tasks: {p.get('tasks')}")
            return p["access_token"]
    sys.exit(f"ERROR: this user token has no access to Page {PAGE}. Pages visible: {[p.get('name') for p in r.json().get('data', [])]}")

def main(path, caption):
    TOKEN = page_token(os.environ["FB_PAGE_TOKEN"])
    size = os.path.getsize(path)
    r = requests.post(f"{G}/{PAGE}/video_reels", json={"upload_phase": "start", "access_token": TOKEN}, timeout=60)
    if r.status_code >= 400: print(r.text)
    r.raise_for_status(); vid = r.json()["video_id"]
    print("started upload, video_id", vid)
    with open(path, "rb") as f:
        r = requests.post(f"https://rupload.facebook.com/video-upload/{V}/{vid}",
                          headers={"Authorization": f"OAuth {TOKEN}", "offset": "0", "file_size": str(size)},
                          data=f, timeout=300)
    if r.status_code >= 400: print(r.text)
    r.raise_for_status(); print("uploaded", r.json())
    r = requests.post(f"{G}/{PAGE}/video_reels",
                      data={"access_token": TOKEN, "video_id": vid, "upload_phase": "finish",
                            "video_state": "PUBLISHED", "description": caption}, timeout=60)
    if r.status_code >= 400: print(r.text)
    r.raise_for_status(); print("publish requested", r.json())
    for _ in range(20):
        time.sleep(15)
        s = requests.get(f"{G}/{vid}", params={"fields": "status", "access_token": TOKEN}, timeout=30)
        if s.ok:
            st = s.json().get("status", {})
            print("status", st)
            if st.get("video_status") in ("ready", "error"): break
    print(f"REEL_ID={vid}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
