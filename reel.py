#!/usr/bin/env python3
"""Candle & Code Reel engine: JSON spec -> 1080x1920 MP4 with music bed.
usage: python3 reel.py spec.json out.mp4"""
import json, sys, math, subprocess, wave, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
BG=(14,17,22); FG=(230,237,243); GREEN=(61,220,151); RED=(255,92,92); MUT=(125,133,144); GRID=(24,29,37)
FD=os.environ.get("FONT_DIR","/usr/share/fonts/truetype/google-fonts/").rstrip("/")+"/"
def F(w,s): return ImageFont.truetype(FD+f"Poppins-{w}.ttf", s)
MONO=lambda s: ImageFont.truetype(os.environ.get("MONO_FONT","/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"), s)
COL={"fg":FG,"green":GREEN,"red":RED,"muted":MUT}

def ease(t): t=max(0,min(1,t)); return 1-(1-t)**3
def pop(t):
    t=max(0,min(1,t)); return 1+0.12*math.sin(t*math.pi)*(1-t) if t<1 else 1

BASE=Image.new("RGB",(W,H),BG)
d=ImageDraw.Draw(BASE)
for x in range(0,W,90): d.line([(x,0),(x,H)],fill=GRID,width=1)
for y in range(0,H,90): d.line([(0,y),(W,y)],fill=GRID,width=1)
vign=Image.new("L",(W,H),0); ImageDraw.Draw(vign).ellipse([-300,200,W+300,H-200],fill=255)
vign=vign.filter(ImageFilter.GaussianBlur(200))
BASE=Image.composite(BASE,Image.new("RGB",(W,H),(8,10,13)),vign)

def text_c(img,y,txt,font,fill,scale=1.0,alpha=1.0):
    if alpha<=0: return
    layer=Image.new("RGBA",(W,H),(0,0,0,0)); dd=ImageDraw.Draw(layer)
    bb=dd.textbbox((0,0),txt,font=font); tw,th=bb[2]-bb[0],bb[3]-bb[1]
    if scale!=1.0:
        f2=ImageFont.truetype(font.path,max(8,int(font.size*scale))); bb=dd.textbbox((0,0),txt,font=f2); tw,th=bb[2]-bb[0],bb[3]-bb[1]; font=f2
    dd.text(((W-tw)/2-bb[0],y-th/2-bb[1]),txt,font=font,fill=fill+(int(255*alpha),))
    img.alpha_composite(layer)

def wrap(txt,font,maxw):
    words=txt.split(); lines=[]; cur=""
    dd=ImageDraw.Draw(BASE)
    for w_ in words:
        t=(cur+" "+w_).strip()
        if dd.textlength(t,font=font)<=maxw: cur=t
        else: lines.append(cur); cur=w_
    if cur: lines.append(cur)
    return lines

def mark(img,cx,cy,s,alpha=1.0):
    dd=ImageDraw.Draw(img); a=int(255*alpha); k=s/100
    g=GREEN+(a,); m=MUT+(a,)
    dd.line([(cx-20*k,cy-16*k),(cx-34*k,cy),(cx-20*k,cy+16*k)],fill=m,width=max(2,int(3*k)),joint="curve")
    dd.line([(cx+20*k,cy-16*k),(cx+34*k,cy),(cx+20*k,cy+16*k)],fill=m,width=max(2,int(3*k)),joint="curve")
    dd.line([(cx,cy-30*k),(cx,cy+30*k)],fill=g,width=max(2,int(3*k)))
    dd.rounded_rectangle([cx-8*k,cy-16*k,cx+8*k,cy+14*k],radius=2*k,fill=g)

def scene_frame(sc,t,img):
    typ=sc["type"]; dur=sc["dur"]
    if typ=="hook":
        lines=sc["lines"]; n=len(lines); step=min(0.6,dur/(n+1))
        y0=H*0.42-(n-1)*110
        for i,ln in enumerate(lines):
            lt=(t-i*step)/0.25
            if lt<0: continue
            sz=sc.get("size",130)
            text_c(img,y0+i*220,ln["t"],F("Bold",sz),COL[ln.get("c","fg")],scale=pop(lt) if lt<1 else 1,alpha=ease(lt*2))
    elif typ=="text":
        font=F(sc.get("weight","Bold"),sc.get("size",96)); lines=[]
        for para in sc["lines"]:
            for l in wrap(para["t"],font,W-160): lines.append((l,COL[para.get("c","fg")]))
        lh=font.size*1.3; y0=H*0.45-(len(lines)-1)*lh/2
        per=min(0.45,(dur-0.6)/max(1,len(lines)))
        for i,(l,c) in enumerate(lines):
            lt=(t-0.1-i*per)/0.35
            if lt<0: continue
            e=ease(lt); text_c(img,y0+i*lh+(1-e)*40,l,font,c,alpha=e)
    elif typ=="bars":
        text_c(img,H*0.23,sc["title"],F("Bold",64),FG,alpha=ease(t/0.3))
        if sc.get("subtitle"): text_c(img,H*0.23+80,sc["subtitle"],F("Regular",38),MUT,alpha=ease((t-0.2)/0.3))
        rows=sc["rows"]; mx=max(r["v"] for r in rows); per=(dur-1.2)/len(rows)
        dd=ImageDraw.Draw(img); top=H*0.36; rh=190
        for i,r in enumerate(rows):
            lt=(t-0.5-i*per)/0.6
            if lt<0: continue
            e=ease(lt); y=top+i*rh; a=int(255*min(1,lt*2))
            dd.text((90,y),r["l"],font=F("Bold",60),fill=COL[r.get("lc","red")]+(a,))
            bx=90; by=y+86; bw=(W-180)*(r["v"]/mx)*e
            dd.rounded_rectangle([bx,by,bx+W-180,by+44],radius=22,fill=(30,36,46,a))
            bw=max(bw,44*e)
            if bw>1: dd.rounded_rectangle([bx,by,bx+bw,by+44],radius=22,fill=COL[r.get("bc","green")]+(a,))
            val=r["vl"]; vf=F("Bold",60); vw=dd.textlength(val,font=vf)
            dd.text((W-90-vw,y),val,font=vf,fill=COL[r.get("bc","green")]+(a,))
    elif typ=="stat":
        e=ease(t/0.35)
        text_c(img,H*0.36,sc.get("label",""),F("Regular",46),MUT,alpha=e)
        text_c(img,H*0.45,sc["value"],F("Bold",sc.get("size",190)),COL[sc.get("c","green")],scale=pop(t/0.3) if t<0.3 else 1,alpha=e)
        if sc.get("note"):
            f=F("Bold",60)
            for i,l in enumerate(wrap(sc["note"],f,W-180)):
                lt=(t-0.5-i*0.3)/0.35
                if lt>0: text_c(img,H*0.57+i*80,l,f,FG,alpha=ease(lt))
    elif typ=="code":
        dd=ImageDraw.Draw(img); f=MONO(sc.get("size",54)); lh=f.size*1.55
        lines=sc["lines"]; y0=H*0.45-(len(lines)-1)*lh/2
        box=[70,y0-lh,W-70,y0+len(lines)*lh]
        dd.rounded_rectangle(box,radius=28,fill=(20,24,31,255),outline=(40,47,58,255),width=2)
        for k,c in enumerate([(255,95,86),(255,189,46),(39,201,63)]): dd.ellipse([100+k*40,y0-lh+22,122+k*40,y0-lh+44],fill=c+(255,))
        total_chars=sum(len(l["t"]) for l in lines); cps=total_chars/max(0.5,dur-1.0)
        shown=int(t*cps); x0=110
        for i,l in enumerate(lines):
            n=min(len(l["t"]),max(0,shown)); shown-=len(l["t"])
            if n<=0: break
            dd.text((x0,y0+i*lh),l["t"][:n],font=f,fill=COL[l.get("c","fg")]+(255,))
    elif typ=="end":
        e=ease(t/0.5); mark(img,W/2,H*0.40,260,alpha=e)
        text_c(img,H*0.40+220,"candle&code",MONO(84),FG,alpha=e)
        if sc.get("line"): text_c(img,H*0.40+330,sc["line"],MONO(38),MUT,alpha=ease((t-0.4)/0.5))

def render(spec,out):
    scenes=spec["scenes"]; total=sum(s["dur"] for s in scenes); nf=int(total*FPS)
    tmp=out+".v.mp4"
    p=subprocess.Popen(["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pix_fmt","rgb24","-s",f"{W}x{H}","-r",str(FPS),"-i","-",
        "-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p",tmp],stdin=subprocess.PIPE)
    starts=np.cumsum([0]+[s["dur"] for s in scenes])
    for fi in range(nf):
        t=fi/FPS; si=int(np.searchsorted(starts,t,side="right")-1); si=min(si,len(scenes)-1)
        st=t-starts[si]; sc=scenes[si]
        img=BASE.convert("RGBA")
        scene_frame(sc,st,img)
        if sc["type"]!="end" and spec.get("tag"):
            text_c(img,190,spec["tag"],MONO(34),GREEN,alpha=0.9)
        dd=ImageDraw.Draw(img); dd.rectangle([0,0,W,10],fill=(30,36,46,255)); dd.rectangle([0,0,W*t/total,10],fill=GREEN+(255,))
        if spec.get("footer") and sc["type"]!="end": text_c(img,H-330,spec["footer"],F("Regular",30),MUT,alpha=0.8)
        fr=img.convert("RGB")
        if st<0.12 and si>0:
            fr=Image.blend(fr,Image.new("RGB",(W,H),(40,48,60)),0.35*(1-st/0.12))
        p.stdin.write(fr.tobytes())
    p.stdin.close(); p.wait()
    wav=out+".a.wav"; music(total,[float(x) for x in starts[1:-1]],wav,spec.get("bpm",100))
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",tmp,"-i",wav,"-c:v","copy","-c:a","aac","-b:a","160k","-ar","48000","-ac","2","-shortest","-movflags","+faststart",out],check=True)
    os.remove(tmp); os.remove(wav)

def music(total,cuts,path,bpm):
    sr=44100; n=int(total*sr); t=np.arange(n)/sr; x=np.zeros(n)
    beat=60/bpm
    for f,a in [(110,.05),(130.8,.035),(164.8,.03),(220,.02)]:
        x+=a*np.sin(2*np.pi*f*t)*(0.6+0.4*np.sin(2*np.pi*t/8))
    kl=int(.25*sr); kt=np.arange(kl)/sr; kick=np.sin(2*np.pi*(50+90*np.exp(-kt*30))*kt)*np.exp(-kt*12)*0.5
    b=0.0
    while b<total-0.3:
        i=int(b*sr); x[i:i+kl]+=kick[:max(0,min(kl,n-i))]; b+=beat
    hl=int(.05*sr); hat=np.random.RandomState(1).randn(hl)*np.exp(-np.arange(hl)/sr*80)*0.06
    b=beat/2
    while b<total-0.3:
        i=int(b*sr); x[i:i+hl]+=hat[:max(0,min(hl,n-i))]; b+=beat
    wl=int(.35*sr); wn=np.random.RandomState(2).randn(wl); env=np.sin(np.linspace(0,np.pi,wl))**2*0.12
    for c in cuts:
        i=max(0,int((c-0.2)*sr)); x[i:i+wl]+=(wn*env)[:max(0,min(wl,n-i))]
    fade=np.minimum(1,np.minimum(t/0.3,(total-t)/0.8)); x*=fade
    x=np.tanh(x*1.4)*0.8
    with wave.open(path,"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x*32767).astype(np.int16).tobytes())

if __name__=="__main__":
    render(json.load(open(sys.argv[1])),sys.argv[2])
