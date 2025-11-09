# audio_mixer.py
from pydub import AudioSegment
from pydub.generators import Sine
import os
from django.conf import settings


def create_alternating_audio(input_mp3_path, output_path, duration_minutes=1):
    """
    Creates a new audio file that alternates between:
    - Original MP3
    - 1 second of silence

    Repeats this pattern for the specified duration (default: 1 minute)

    Args:
        input_mp3_path: Path to the input MP3 file
        output_path: Path to save the output file
        duration_minutes: Total duration of the output in minutes (default: 1)
    """

    if not os.path.exists(input_mp3_path):
        raise FileNotFoundError(f"Input file not found: {input_mp3_path}")

    # Load the MP3 file
    print(f"Loading MP3 file: {input_mp3_path}")
    original_audio = AudioSegment.from_mp3(input_mp3_path)

    # Create 1 second of silence
    silence = AudioSegment.silent(duration=1000)  # 1000ms = 1 second

    # Calculate total duration in milliseconds
    total_duration_ms = duration_minutes * 60 * 1000

    # Build the combined audio
    print(f"Creating alternating pattern for {duration_minutes} minute(s)...")
    combined_audio = AudioSegment.empty()
    elapsed_time = 0

    while elapsed_time < total_duration_ms:
        # Add the original audio
        combined_audio += original_audio
        elapsed_time += len(original_audio)
        print(elapsed_time, total_duration_ms)
        if elapsed_time < total_duration_ms:
            # Add silence (but only if we haven't exceeded total duration)
            remaining_duration = total_duration_ms - elapsed_time
            silence_duration = min(len(silence), remaining_duration)
            silence_to_add = AudioSegment.silent(duration=silence_duration)
            combined_audio += silence_to_add
            elapsed_time += len(silence_to_add)

    # Trim to exact duration if necessary
    combined_audio = combined_audio[:total_duration_ms]

    # Export the file
    print(f"Exporting to: {output_path}")
    combined_audio.export(output_path, format="mp3", bitrate="192k")
    print(f"Done! File saved to {output_path}")
    print(f"Total duration: {len(combined_audio) / 1000 / 60:.2f} minutes")


input_mp3 = "alarm.mp3"  # Replace with your MP3 file path
output_mp3 = "long_alarm.mp3"  # Output file name

create_alternating_audio(input_mp3, output_mp3, duration_minutes=1)
