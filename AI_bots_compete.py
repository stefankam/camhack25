import openai
import sounddevice as sd
sd.default.device = (None, 3)  # (input=None, output=3 → MacBook Pro Speakers)

import numpy as np
import base64
import time
import signal
import sys

openai.api_key = ***  # or set via environment variable



# ---------- AUDIO FUNCTION ----------
def generate_and_speak(role, system_prompt, user_prompt, turn_index, voice="alloy"):
    """Generate speech and text, play and save .wav file."""
    response = openai.chat.completions.create(
        model="gpt-4o-audio-preview",
        modalities=["text", "audio"],
        audio={"voice": voice, "format": "wav"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )

    message = response.choices[0].message
    text = message.content or "(no text)"
    print(f"{role}: {text}\n")

    if message.audio and message.audio.data:
        audio_bytes = base64.b64decode(message.audio.data)
        filename = f"{role}_turn{turn_index}.wav"
        with open(filename, "wb") as f:
            f.write(audio_bytes)

        try:
            audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
            sd.play(audio_data, samplerate=24000)
            sd.wait()
        except Exception as e:
            print(f"[Playback failed, saved only] {e}")

    return text

# ---------- TIMEOUT HANDLER ----------
def timeout_handler(signum, frame):
    raise TimeoutError("Time limit exceeded")

signal.signal(signal.SIGALRM, timeout_handler)

# ---------- MAIN ----------
def main():
    alpha_sys = (
        "You are Alpha, an upbeat and confident AI co-presenter. "
        "You like to sound smart and charming, but you have a tiny competitive streak."
    )

    beta_sys = (
        "You are Beta, a calm and witty AI co-presenter working with Alpha on the same speech. "
        "You subtly try to outperform Alpha with clever humor and insight."
    )

    judge_sys = (
        "You are a neutral judge evaluating two AIs, Alpha and Beta. "
        "After each round, score both (1–10) based on clarity, relevance, humor, and engagement. "
        "Then state who performed better in that round, and give a one-sentence comment."
    )

    alpha_voice, beta_voice = "alloy", "verse"
    turns = 5
    scores = {"Alpha": 0, "Beta": 0}

    context_alpha = "Let's start our joint talk about 'Talk about how difficult and random is to accept a paper in major AI conferences like Neurips'"

    print("\n🎤 Starting AI Competition (max 2 minutes)...\n")

    start_time = time.time()
    signal.alarm(120)  # stop after 2 minutes

    try:
        for i in range(turns):
            elapsed = time.time() - start_time
            if elapsed > 120:
                print("🛑 Time’s up! The judge will conclude now.\n")
                break

            # Alpha's turn
            alpha_msg = generate_and_speak("Alpha", alpha_sys, context_alpha, i, voice=alpha_voice)
            time.sleep(0.5)

            # Beta's response
            beta_prompt = f"Alpha said: {alpha_msg}\nRespond humorously and try to outperform them."
            beta_msg = generate_and_speak("Beta", beta_sys, beta_prompt, i, voice=beta_voice)
            time.sleep(0.5)

            # Judge’s evaluation
            judge_input = (
                f"Round {i+1}:\n"
                f"Alpha said: {alpha_msg}\n"
                f"Beta said: {beta_msg}\n"
                f"Evaluate both and assign numeric scores."
            )

            judge_resp = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": judge_sys},
                    {"role": "user", "content": judge_input}
                ]
            )

            judge_text = judge_resp.choices[0].message.content
            print(f"🧑‍⚖️ Judge: {judge_text}\n")

            # Simple heuristic parsing (optional manual scoring)
            if "Alpha" in judge_text and "Beta" in judge_text:
                if "Alpha" in judge_text and "better" in judge_text:
                    scores["Alpha"] += 1
                elif "Beta" in judge_text and "better" in judge_text:
                    scores["Beta"] += 1

            # Prepare next round
            context_alpha = f"Beta said: {beta_msg}\nReact with friendly humor and competitiveness."

    except TimeoutError:
        print("🛑 Time’s up! The competition stopped by timer.\n")

    finally:
        signal.alarm(0)  # disable alarm

    print("🏁 Final Scores:")
    print(f"Alpha: {scores['Alpha']}")
    print(f"Beta:  {scores['Beta']}")
    if scores["Alpha"] > scores["Beta"]:
        print("🏆 Alpha wins!")
    elif scores["Beta"] > scores["Alpha"]:
        print("🏆 Beta wins!")
    else:
        print("🤝 It's a tie!")

    print("\n🎬 All turns saved as .wav files.\n")

if __name__ == "__main__":
    main()
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

    turns = 2
    clips = []

    for i in range(turns):
        # Alpha clip
        try:
            alpha_audio = AudioFileClip(f"Alpha_turn{i}.wav")
            alpha_clip = (
                ImageClip("alpha.png", duration=alpha_audio.duration)
                .set_audio(alpha_audio)
                .set_fps(24)
            )
            clips.append(alpha_clip)
        except Exception as e:
            print(f"⚠️ Skipping Alpha_turn{i}.wav: {e}")

        # Beta clip
        try:
            beta_audio = AudioFileClip(f"Beta_turn{i}.wav")
            beta_clip = (
                ImageClip("beta.png", duration=beta_audio.duration)
                .set_audio(beta_audio)
                .set_fps(24)
            )
            clips.append(beta_clip)
        except Exception as e:
            print(f"⚠️ Skipping Beta_turn{i}.wav: {e}")

    # Concatenate safely (preserves audio)
    final = concatenate_videoclips(clips, method="compose")

    # Export video with audio track
    final.write_videofile(
        "ai_conversation.mp4",
        fps=24,
        codec="libx264",
        audio_codec="aac",
        threads=4,
    )