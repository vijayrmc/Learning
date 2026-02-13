from youtube_transcript_api import YouTubeTranscriptApi
import subprocess
import tempfile
import os
import re
import logging

logger = logging.getLogger(__name__)

def fetch_transcript(url: str) -> str:
    video_id = None
    if "v=" in url:
        video_id = url.split("v=")[1].split("&")[0]
    elif "be/" in url:
        video_id = url.split("be/")[1].split("?")[0]
        
    if not video_id: return ""
    
    # Strategy 1: youtube-transcript-api (Most efficient)
    try:
        # Try different possible method names or direct fetch
        proxy = YouTubeTranscriptApi
        
        # Check if it has list_transcripts (standard)
        if hasattr(proxy, 'list_transcripts'):
            transcript_list = proxy.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
            except:
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except:
                    transcript = transcript_list.find_transcript(['en'])
            data = transcript.fetch()
            return " ".join([t['text'] for t in data])
        
        # Fallback to get_transcript if list_transcripts is missing
        if hasattr(proxy, 'get_transcript'):
            data = proxy.get_transcript(video_id)
            return " ".join([t['text'] for t in data])
            
    except Exception as e:
        logger.warning(f"youtube-transcript-api failed for {video_id}: {e}")

    # Strategy 2: yt-dlp (Robust fallback)
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # -f best: don't download, just need subs
            # --write-auto-subs: get auto-generated if manual missing
            # --skip-download: only subs
            cmd = [
                "python", "-m", "yt_dlp",
                "--skip-download",
                "--write-auto-subs",
                "--sub-lang", "en.*",
                "--sub-format", "vtt",
                "-o", f"{tmpdir}/sub",
                url
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            sub_file = None
            for f in os.listdir(tmpdir):
                if f.startswith("sub") and f.endswith(".vtt"):
                    sub_file = os.path.join(tmpdir, f)
                    break
            
            if sub_file:
                with open(sub_file, "r", encoding="utf-8") as f:
                    vtt_content = f.read()
                    # Clean VTT: remove headers, timestamps, and tags
                    text = re.sub(r'WEBVTT|KIND|LANGUAGE|STYLE|NOTE.*?\n', '', vtt_content)
                    text = re.sub(r'\d{2}:\d{2}:\d{2}.\d{3} --> \d{2}:\d{2}:\d{2}.\d{3}.*?\n', '', text)
                    text = re.sub(r'<.*?>', '', text)
                    text = re.sub(r'\n+', ' ', text)
                    return text.strip()
                    
    except Exception as e:
        logger.error(f"yt-dlp fallback failed for {video_id}: {e}")
        
    return ""
