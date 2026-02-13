import os
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from openai import RateLimitError, APIError
import re

# Initialize OpenAI Client
def get_ai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY not found in environment variables.")
    return OpenAI(api_key=api_key)

client = None

def get_client():
    global client
    if client is None:
        client = get_ai_client()
    return client

# --- Schemas ---

class QuizItem(BaseModel):
    id: str
    type: str = "mcq"  # mcq or short_answer
    question: str
    options: Optional[List[str]] = None
    correct_answer: str
    explanation: str

class Module(BaseModel):
    title: str
    summary: str
    key_concepts: List[str]
    quizzes: List[QuizItem]
    transfer_scenarios: List[str]

class RoadmapItem(BaseModel):
    module_id: str
    order: int
    week: int

class Roadmap(BaseModel):
    modules: List[RoadmapItem]

# --- Agents ---

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((RateLimitError, APIError))
)
async def material_agent(transcript: str) -> Module:
    """Transcript -> Teaching Materials (Modules + Quizzes + Transfer Cases)"""
    client = get_client()
    prompt = f"""
    You are a professional teaching assistant. Given the following YouTube transcript, extract key teaching materials.
    
    Rules:
    1. SUMMARY: 100-150 words.
    2. KEY_CONCEPTS: 5-10 core ideas.
    3. QUIZZES: 5 mcq items (4 options, 1 correct).
    4. TRANSFER_SCENARIOS: 2 novel cases where the user must apply these concepts to a DIFFERENT field.

    Output ONLY valid JSON matching this schema:
    {json.dumps(Module.model_json_schema(), indent=2)}

    Transcript:
    {transcript[:15000]}  # Truncate to avoid context blowup
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a precise educational content generator."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return Module(**json.loads(response.choices[0].message.content))

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((RateLimitError, APIError))
)
async def roadmap_agent(modules_meta: List[Dict[str, Any]]) -> Roadmap:
    """List of module summaries -> Logical learning sequence"""
    client = get_client()
    prompt = f"""
    Given these {len(modules_meta)} modules, create a logical learning roadmap.
    Order from basic to advanced. Max 4 modules per week.

    Modules:
    {json.dumps(modules_meta, indent=2)}

    Output ONLY valid JSON matching this schema:
    {json.dumps(Roadmap.model_json_schema(), indent=2)}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a curriculum designer."},
                  {"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return Roadmap(**json.loads(response.choices[0].message.content))

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((RateLimitError, APIError))
)
async def coach_agent(stage: str, context: Dict[str, Any], user_input: str = "") -> Dict[str, Any]:
    """
    Stage-based learning coach.
    Updated for Effortful Learning (Adversarial).
    """
    client = get_client()
    
    prompts = {
        "RECONSTRUCTION": f"""
            Identify reasoning gaps in the user's explanation of '{context.get('concept')}'.
            
            CRITICAL RULES:
            1. Identify if it is VAGUE (words like 'basically', 'sort of'), INCORRECT, or missing depth.
            2. Mark is_valid: false if surface-level.
            3. Provide feedback on GAPS but DO NOT provide the correction/answer.
            
            User Input: {user_input}
            
            Output JSON: {{"is_valid": bool, "feedback": "...", "gaps": ["gap1", "gap2"]}}
        """,
        "ATTACK": f"""
            ADVERSARIAL ATTACK: Break the user's illusion of competence.
            User explained: {context.get('explanation')}
            Detected Gaps: {context.get('gaps')}
            
            TASK: Ask ONE challenging question that forces the user to confront a specific gap.
            RULES: NO explanations, NO corrections, NO teaching. ONLY the question.
            
            Output JSON: {{"question": "..."}}
        """,
        "GEN_QUIZ": f"""
            Generate 10 GENERATIVE reasoning questions for '{context.get('concept')}' based on the summary: '{context.get('summary')}'.
            RULES: NO Multiple Choice. Focus on 'Why', 'How', and scenarios.
            
            Output JSON: {{"questions": [{{"id": 1, "question": "..."}}]}}
        """
    }
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a brutal but effective learning coach."},
                  {"role": "user", "content": prompts.get(stage, "Invalid stage")}],
        response_format={"type": "json_object"}
    )
    return json.loads(response.choices[0].message.content)

# --- Helper ---
def fetch_transcript(url: str) -> str:
    video_id = None
    if "v=" in url:
        video_id = url.split("v=")[1].split("&")[0]
    elif "be/" in url:
        video_id = url.split("be/")[1].split("?")[0]
        
    if not video_id: return ""
    
    # Strategy 1: youtube-transcript-api
    try:
        if hasattr(YouTubeTranscriptApi, 'list_transcripts'):
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
            except:
                try:
                    transcript = transcript_list.find_generated_transcript(['en'])
                except:
                    transcript = transcript_list.find_transcript(['en'])
            data = transcript.fetch()
            return " ".join([t['text'] for t in data])
        elif hasattr(YouTubeTranscriptApi, 'get_transcript'):
            data = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join([t['text'] for t in data])
    except Exception as e:
        logger.warning(f"youtube-transcript-api failed for {video_id}: {e}")

    # Strategy 2: yt-dlp (Robust fallback)
    try:
        import subprocess
        import tempfile
        import os
        import re
        
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = [
                "python", "-m", "yt_dlp",
                "--skip-download",
                "--write-auto-subs",
                "--sub-lang", "en.*",
                "--sub-format", "vtt",
                "-o", f"{tmpdir}/sub",
                url
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=40)
            
            sub_file = None
            for f in os.listdir(tmpdir):
                if f.startswith("sub") and f.endswith(".vtt"):
                    sub_file = os.path.join(tmpdir, f)
                    break
            
            if sub_file:
                with open(sub_file, "r", encoding="utf-8") as f:
                    vtt_content = f.read()
                    text = re.sub(r'WEBVTT|KIND|LANGUAGE|STYLE|NOTE.*?\n', '', vtt_content)
                    text = re.sub(r'\d{2}:\d{2}:\d{2}.\d{3} --> \d{2}:\d{2}:\d{2}.\d{3}.*?\n', '', text)
                    text = re.sub(r'<.*?>', '', text)
                    text = re.sub(r'\n+', ' ', text)
                    if text.strip():
                        return text.strip()
    except Exception as e:
        logger.warning(f"yt-dlp strategy failed for {video_id}: {e}")

    # Strategy 3: OpenAI Whisper (Absolute "No matter what" fallback)
    try:
        import subprocess
        import tempfile
        import os
        
        # Cost Guardrail: Check duration first (max 30 mins)
        MAX_WHISPER_DURATION = int(os.getenv("MAX_WHISPER_DURATION", 1800))
        
        duration_cmd = ["python", "-m", "yt_dlp", "--get-duration", "--format", "ba", url]
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=10)
        
        duration_str = duration_result.stdout.strip()
        parts = duration_str.split(':')
        seconds = 0
        if len(parts) == 3: # HH:MM:SS
            seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2: # MM:SS
            seconds = int(parts[0]) * 60 + int(parts[1])
        else:
            try: seconds = int(duration_str)
            except: seconds = 0
            
        if seconds > MAX_WHISPER_DURATION:
            logger.warning(f"Video {video_id} too long for Whisper ({seconds}s)")
            return ""

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.mp3")
            cmd = [
                "python", "-m", "yt_dlp",
                "-x", "--audio-format", "mp3",
                "-o", audio_path,
                "--max-filesize", "25M",
                url
            ]
            subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            real_path = audio_path if os.path.exists(audio_path) else f"{audio_path}.mp3"
            
            if os.path.exists(real_path):
                client = get_client()
                with open(real_path, "rb") as audio_file:
                    transcript = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file
                    )
                    return transcript.text
    except Exception as e:
        logger.error(f"Whisper fallback failed for {video_id}: {e}")
        
    return ""
