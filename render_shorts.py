import os
import sys
import json
import asyncio
import requests
import datetime
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import edge_tts

# Pexels API configuration
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY", "")
DEFAULT_VOICE = "ko-KR-SunHiNeural"  # Default Korean female voice

async def generate_tts(text, voice, output_audio, output_vtt):
    print(f"[TTS] Generating speech for: {text[:30]}...")
    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()
    
    with open(output_audio, "wb") as fp:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                fp.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset and duration are in 100-nanosecond intervals
                offset = chunk["offset"]
                duration = chunk["duration"]
                
                # Convert to datetime.timedelta (1 microsecond = 10 * 100ns)
                start = datetime.timedelta(microseconds=offset // 10)
                end = datetime.timedelta(microseconds=(offset + duration) // 10)
                
                submaker.create_sub((start, end), chunk["text"])
                
    with open(output_vtt, "w", encoding="utf-8") as f:
        f.write(submaker.generate_subs())
    print("[TTS] Speech and VTT subtitles generated.")

def search_pexels_videos(query, api_key, min_duration=10):
    if not api_key:
        print("[Pexels] API Key missing. Skipping video search.")
        return []
    
    headers = {"Authorization": api_key}
    # Search vertical orientation (9:16 preferred)
    url = f"https://api.pexels.com/videos/search?query={query}&per_page=15&orientation=portrait"
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"[Pexels] Vertical search failed with status {response.status_code}. Trying general search...")
            url = f"https://api.pexels.com/videos/search?query={query}&per_page=15"
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                return []
            
        data = response.json()
        videos = data.get("videos", [])
        
        download_urls = []
        for v in videos:
            if v.get("duration", 0) < min_duration:
                continue
            video_files = v.get("video_files", [])
            
            # Find high quality MP4
            best_file = None
            for vf in video_files:
                if vf.get("file_type") == "video/mp4":
                    best_file = vf.get("link")
                    # Break on HD quality
                    if vf.get("height") >= 720:
                        break
            if best_file:
                download_urls.append(best_file)
        return download_urls
    except Exception as e:
        print(f"[Pexels] Exception during search: {e}")
        return []

def download_file(url, local_path):
    print(f"[Downloader] Downloading {url}...")
    try:
        response = requests.get(url, stream=True, timeout=30)
        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"[Downloader] Failed to download {url}: {e}")
        return False

def crop_to_9_16(clip):
    # Target aspect ratio: width = height * 9 / 16
    target_w = int(clip.h * 9 / 16)
    if target_w <= clip.w:
        # horizontal center crop
        x1 = (clip.w - target_w) // 2
        x2 = x1 + target_w
        return clip.crop(x1=x1, y1=0, x2=x2, y2=clip.h)
    else:
        # vertical center crop
        target_h = int(clip.w * 16 / 9)
        y1 = (clip.h - target_h) // 2
        y2 = y1 + target_h
        return clip.crop(x1=0, y1=y1, x2=clip.w, y2=y2)

def edit_video(video_paths, audio_path, total_duration):
    print(f"[VideoEditor] Editing video. Total duration required: {total_duration:.2f}s")
    clips = []
    
    current_duration = 0
    for vp in video_paths:
        if current_duration >= total_duration:
            break
        try:
            clip = VideoFileClip(vp)
            clip = clip.without_audio()
            
            # Crop and resize to standard vertical HD (1080x1920)
            clip = crop_to_9_16(clip).resize((1080, 1920))
            
            remaining = total_duration - current_duration
            if clip.duration > remaining:
                clip = clip.subclip(0, remaining)
            
            clips.append(clip)
            current_duration += clip.duration
        except Exception as e:
            print(f"[VideoEditor] Error processing {vp}: {e}")

    if not clips:
        raise ValueError("No video clips could be successfully processed.")

    # Concat clips
    final_video = concatenate_videoclips(clips, method="compose")
    
    # Load TTS Audio
    audio = AudioFileClip(audio_path)
    final_video = final_video.set_audio(audio)
    
    # Write temp clip without subtitles
    temp_path = "temp_no_subs.mp4"
    final_video.write_videoclip(temp_path, fps=24, codec="libx264", audio_codec="aac", temp_audiofile="temp_audio.m4a", remove_temp=True)
    
    # Cleanup clips
    for c in clips:
        c.close()
    audio.close()
    final_video.close()
    return temp_path

def burn_subtitles(video_path, vtt_path, output_path):
    print("[FFmpeg] Burning subtitles into video...")
    # Escape path characters for FFmpeg subtitles filter
    vtt_escaped = vtt_path.replace(":", "\\:").replace("'", "'\\\\''")
    
    # ASS Formatting style: NanumBarunGothic, white, outline 2.5px, aligned at the bottom (MarginV=180 to clear YouTube shorts UI)
    style = "Fontname=NanumBarunGothic,Fontsize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2.5,Alignment=2,MarginV=180"
    
    cmd = f"ffmpeg -i {video_path} -vf \"subtitles={vtt_escaped}:force_style='{style}'\" -c:v libx264 -c:a copy -y {output_path}"
    print(f"[FFmpeg] Running command: {cmd}")
    ret = os.system(cmd)
    if ret != 0:
        print(f"[FFmpeg] Command failed with exit code {ret}")
        return False
    return True

async def main():
    input_json = "/data/shorts_input.json"
    if not os.path.exists(input_json):
        print(f"Error: Input JSON file not found at {input_json}")
        sys.exit(1)
        
    with open(input_json, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    script = data.get("script")
    search_query = data.get("search_query", "news")
    output_name = data.get("output_name", "output.mp4")
    voice = data.get("voice", DEFAULT_VOICE)
    
    if not script:
        print("Error: 'script' is required in shorts_input.json")
        sys.exit(1)
        
    output_video_path = f"/data/{output_name}"
    audio_path = "tts.mp3"
    vtt_path = "subs.vtt"
    
    # 1. Generate TTS
    await generate_tts(script, voice, audio_path, vtt_path)
    
    # Get audio duration
    audio_clip = AudioFileClip(audio_path)
    audio_duration = audio_clip.duration
    audio_clip.close()
    print(f"TTS Duration: {audio_duration:.2f} seconds")
    
    # 2. Fetch background videos
    print(f"Searching videos on Pexels for query: '{search_query}'")
    video_urls = search_pexels_videos(search_query, PEXELS_API_KEY, min_duration=audio_duration/2)
    
    if not video_urls:
        print("No videos found on Pexels. Trying fallback search 'nature'...")
        video_urls = search_pexels_videos("nature", PEXELS_API_KEY, min_duration=audio_duration/2)
        
    if not video_urls:
        fallback_path = "/data/fallback.mp4"
        if os.path.exists(fallback_path):
            print("Using fallback video: fallback.mp4")
            downloaded_files = [fallback_path]
        else:
            print("Error: No videos found from Pexels and no /data/fallback.mp4 provided.")
            sys.exit(1)
    else:
        # Download top 3 video clips
        downloaded_files = []
        os.makedirs("downloads", exist_ok=True)
        for idx, url in enumerate(video_urls[:3]):
            local_name = f"downloads/video_{idx}.mp4"
            if download_file(url, local_name):
                downloaded_files.append(local_name)
                
        if not downloaded_files:
            print("Error: Failed to download any background videos.")
            sys.exit(1)
            
    # 3. Process video cropping & narration mixing
    try:
        temp_no_subs = edit_video(downloaded_files, audio_path, audio_duration)
    except Exception as e:
        print(f"Error during video editing: {e}")
        sys.exit(1)
        
    # 4. Synthesize subtitles
    success = burn_subtitles(temp_no_subs, vtt_path, output_video_path)
    
    # Clean up temp files
    if os.path.exists("tts.mp3"):
        os.remove("tts.mp3")
    if os.path.exists("subs.vtt"):
        os.remove("subs.vtt")
    if os.path.exists("temp_no_subs.mp4"):
        os.remove("temp_no_subs.mp4")
    # Clean up downloads
    if os.path.exists("downloads"):
        for f in os.listdir("downloads"):
            os.remove(os.path.join("downloads", f))
        os.rmdir("downloads")
        
    if success:
        print(f"Successfully generated shorts video at: {output_video_path}")
    else:
        print("Failed to generate subtitles.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
