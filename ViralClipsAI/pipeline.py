import os, re, subprocess
from pathlib import Path
from yt_dlp import YoutubeDL
from faster_whisper import WhisperModel
from paths import UPLOADS, OUTPUTS, MODELS, resource_path

SUPPORTED_HOSTS = ("youtube.com", "youtu.be", "tiktok.com", "instagram.com")

def ffmpeg_exe():
    bundled = resource_path("ffmpeg/ffmpeg.exe")
    return str(bundled) if bundled.exists() else "ffmpeg"

def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout)[-1800:])
    return p.stdout

def download_source(url, job_id):
    target = str(UPLOADS / f"{job_id}.%(ext)s")
    opts = {"outtmpl": target, "format": "bv*+ba/b", "merge_output_format": "mp4",
            "noplaylist": True, "quiet": True, "no_warnings": True, "ffmpeg_location": str(Path(ffmpeg_exe()).parent)}
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))
    if not path.exists():
        candidates = list(UPLOADS.glob(f"{job_id}.*"))
        if not candidates: raise RuntimeError("No se pudo localizar el video descargado.")
        path = candidates[0]
    return path, info.get("title", "Video")

def transcribe(path):
    model_name = os.getenv("WHISPER_MODEL", "small")
    model = WhisperModel(model_name, device="cpu", compute_type="int8", download_root=str(MODELS))
    segments, _ = model.transcribe(str(path), language="es", word_timestamps=True, vad_filter=True)
    result = []
    for s in segments:
        words = [{"start": float(w.start), "end": float(w.end), "text": w.word.strip()} for w in (s.words or [])]
        result.append({"start": float(s.start), "end": float(s.end), "text": s.text.strip(), "words": words})
    if not result: raise RuntimeError("No se detectó voz. Prueba con un video que tenga audio claro.")
    return result

HOOK_WORDS = {"increíble":3,"nunca":2,"secreto":3,"error":2,"importante":2,"cómo":1,"por qué":2,
              "dinero":2,"mejor":1,"peor":1,"problema":2,"verdad":2,"descubrí":2,"impactante":3,
              "gratis":2,"resultado":1,"pero":.5,"entonces":.5}

def rank_windows(segments, duration, count):
    candidates=[]
    total=max(s["end"] for s in segments)
    step=max(5,duration//3)
    for start in range(0,max(1,int(total-duration)+1),step):
        end=min(total,start+duration)
        chunk=[s for s in segments if s["end"]>start and s["start"]<end]
        txt=" ".join(s["text"] for s in chunk).lower()
        if len(txt.split())<12: continue
        score=sum(v for k,v in HOOK_WORDS.items() if k in txt)
        score+=min(len(txt.split())/duration,3)*1.5
        if re.search(r"\?|!",txt): score+=1
        if start<total*.15: score+=.4
        candidates.append((score,start,end,txt))
    candidates.sort(reverse=True)
    chosen=[]
    for item in candidates:
        if all(abs(item[1]-c[1])>duration*.65 for c in chosen):
            chosen.append(item)
        if len(chosen)>=count: break
    if not chosen:
        chosen=[(0,s,min(total,s+duration),"") for s in range(0,max(1,int(total-duration)+1),duration)][:count]
    return sorted(chosen,key=lambda x:x[1])

def ass_time(t):
    cs=int(round(t*100)); h,cs=divmod(cs,360000); m,cs=divmod(cs,6000); s,cs=divmod(cs,100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def esc(t):
    return t.replace("\\",r"\\").replace("{",r"\{").replace("}",r"\}")

def write_ass(segments,start,end,dest,style):
    header="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Main,Arial,76,&H00FFFFFF,&H0000FFFF,&H00101010,&H80000000,-1,0,0,0,100,100,1,0,1,5,2,2,70,70,250,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events=[]
    for seg in segments:
        for w in seg["words"]:
            a,b=max(start,w["start"]),min(end,w["end"])
            if b<=a: continue
            word=esc(w["text"].upper() if style!="clean" else w["text"])
            events.append(f"Dialogue: 0,{ass_time(a-start)},{ass_time(b-start)},Main,,0,0,0,,{{\\c&H00FFFF&}}{word}{{\\c&HFFFFFF&}}")
    if not events:
        for seg in segments:
            a,b=max(start,seg["start"]),min(end,seg["end"])
            if b>a: events.append(f"Dialogue: 0,{ass_time(a-start)},{ass_time(b-start)},Main,,0,0,0,,{esc(seg['text'])}")
    Path(dest).write_text(header+"\n".join(events),encoding="utf-8")

def make_caption(transcript,title):
    clean=re.sub(r"\s+"," ",transcript).strip()
    if len(clean)>125: clean=clean[:122].rsplit(" ",1)[0]+"..."
    return f"{clean or title} 👀 #viral #parati #shorts"

def process_video(url,job_id,length,count,style):
    video,title=download_source(url,job_id)
    segments=transcribe(video)
    windows=rank_windows(segments,length,count)
    results=[]
    ff=ffmpeg_exe()
    for i,(_,start,end,transcript) in enumerate(windows,1):
        ass=OUTPUTS/f"{job_id}_{i}.ass"
        mp4=OUTPUTS/f"{job_id}_clip_{i}.mp4"
        write_ass(segments,start,end,ass,style)
        # Normalize Windows paths for FFmpeg's subtitles filter.
        ass_arg=str(ass.resolve()).replace("\\","/").replace(":","\\:")
        vf=f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,subtitles='{ass_arg}'"
        run([ff,"-y","-ss",str(start),"-i",str(video),"-t",str(end-start),"-vf",vf,
             "-c:v","libx264","-preset","veryfast","-crf","21","-c:a","aac","-b:a","160k",
             "-movflags","+faststart",str(mp4)])
        results.append({"name":f"Clip {i}","file":mp4.name,"duration":round(end-start),
                        "caption":make_caption(transcript or "Un momento que vale la pena ver",title)})
    return results
