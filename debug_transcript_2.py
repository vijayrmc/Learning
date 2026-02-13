from youtube_transcript_api import YouTubeTranscriptApi

def test():
    print(f"Version: {YouTubeTranscriptApi.__module__}")
    print(f"Dir: {dir(YouTubeTranscriptApi)}")
    
    try:
        # Some versions use list_transcripts, some might be different
        video_id = "axCreWC6AHw"
        # Try get_transcript directly
        t = YouTubeTranscriptApi.get_transcript(video_id)
        print("✅ get_transcript worked")
        print(t[:2])
    except Exception as e:
        print(f"❌ get_transcript failed: {e}")

if __name__ == "__main__":
    test()
