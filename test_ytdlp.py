import subprocess
import json
import logging
import os

logger = logging.getLogger(__name__)

def fetch_transcript_ytdlp(url: str) -> str:
    """Uses yt-dlp to get subtitles/transcript."""
    try:
        # Command to get subtitles in json format
        # --skip-download: don't download the video
        # --write-auto-subs: get auto-generated if manual missing
        # --sub-lang en: prefer English
        # --print-json: gives info about the video
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-subs",
            "--sub-lang", "en.*",
            "--print", "subtitles",
            url
        ]
        # Actually, getting subtitles via yt-dlp to a string is easier with --write-subs --sub-format ttml/vtt
        # But for now, let's try to get the raw subtitle data.
        
        # Alternative: Just get info and check if subtitles exist
        # info_cmd = ["yt-dlp", "--skip-download", "--print-json", url]
        # result = subprocess.run(info_cmd, capture_output=True, text=True)
        # info = json.loads(result.stdout)
        
        # A better way for a string transcript:
        # we can use --get-subs and pipe it, but yt-dlp usually writes files.
        # Let's use a temporary file.
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "yt-dlp",
                "--skip-download",
                "--write-auto-subs",
                "--sub-lang", "en.*",
                "--sub-format", "vtt",
                "-o", f"{tmpdir}/sub",
                url
            ]
            subprocess.run(cmd, capture_output=True, text=True)
            
            # Check for files like sub.en.vtt or sub.en-US.vtt
            sub_file = None
            for f in os.listdir(tmpdir):
                if f.startswith("sub") and f.endswith(".vtt"):
                    sub_file = os.path.join(tmpdir, f)
                    break
            
            if sub_file:
                with open(sub_file, "r", encoding="utf-8") as f:
                    vtt_content = f.read()
                    # Basic VTT parsing (strip headers and timestamps)
                    lines = []
                    for line in vtt_content.split("\n"):
                        if "-->" in line or line.strip().isdigit() or line.startswith("WEBVTT"):
                            continue
                        if line.strip():
                            lines.append(line.strip())
                    return " ".join(lines)
                    
    except Exception as e:
        logger.error(f"yt-dlp extraction failed: {e}")
    return ""

if __name__ == "__main__":
    # Test
    print(fetch_transcript_ytdlp("https://www.youtube.com/watch?v=axCreWC6AHw")[:500])
