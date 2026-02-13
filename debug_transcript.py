from youtube_transcript_api import YouTubeTranscriptApi
import logging

logging.basicConfig(level=logging.INFO)

def debug_transcript(video_id):
    try:
        print(f"Checking video: {video_id}")
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        print("\nAvailable manual transcripts:")
        for t in transcript_list._manually_created_transcripts:
            print(f"- {t}")
        
        print("\nAvailable generated transcripts:")
        for t in transcript_list._generated_transcripts:
            print(f"- {t}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_transcript("axCreWC6AHw")
