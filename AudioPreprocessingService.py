#this is what works
#only look at this for future reference

import sqlite3
import librosa, os
import soundfile as sf
import noisereduce as nr
import numpy as np
import pandas as pd
import time
from DBConfig import DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER, psycopg2



class PreProcessAudio:
    @staticmethod
    def timestamp_to_sample(timestamp_ms, sr):
        return int(timestamp_ms * sr / 1000)



    @staticmethod
    def AdjustKeypressTimestamps(keypresses, start_timestamp, y, sr, trim_ms=60):
        """Returns array of (start_sample, end_sample, key, key_id)"""
        return [
        (PreProcessAudio.timestamp_to_sample(start - start_timestamp - 10, sr), 
        PreProcessAudio.timestamp_to_sample(end - start_timestamp + 25, sr), 
        key,
        key_id)
        for start, end, key, key_id in keypresses
        if (start - start_timestamp - 10) >= 0
        ]
        
        
    @staticmethod
    def detect_sync_tone(y, sr, target_freq=4400, threshold_ratio=5.0):
        """
        Detects the start and end times of a sync tone at a target frequency within the audio.

        Args:
            y (np.ndarray): Audio time series.
            sr (int): Sampling rate of `y`.
            target_freq (float): The frequency of the sync tone to detect (in Hz).
            threshold_ratio (float): Multiplier for the noise level to determine the detection threshold.
                                    A higher ratio means a stricter detection.

        Returns:
            tuple: A tuple (start_time_ms, end_time_ms) representing the start and end
                times of the longest detected sync tone segment in milliseconds.
                Returns (None, None) if no tone is detected.
        """
        # Define n_fft and hop_length explicitly for consistency with librosa's defaults
        # These are the default values used by librosa.stft, essential for frame-to-time conversion.
        n_fft = 2048
        hop_length = 512

        # 1. Perform Short-Time Fourier Transform (STFT)
        # D will have shape (1 + n_fft/2, num_frames)
        D = librosa.stft(y, n_fft=n_fft, hop_length=hop_length)
        magnitudes = np.abs(D) # Get the magnitude spectrogram

        # 2. Identify the target frequency bin
        # Get the frequencies corresponding to each STFT bin
        freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
        # Find the index of the frequency bin closest to the target frequency
        target_freq_idx = np.argmin(np.abs(freqs - target_freq))

        # 3. Extract the magnitude spectrum for the target frequency across all time frames
        # This gives us the energy of the target frequency over time.
        target_energy = magnitudes[target_freq_idx, :]

        # 4. Calculate a noise/background level
        # Using the median is robust as it's less affected by outliers (like the tone itself).
        noise_level = np.median(target_energy)

        # 5. Determine a threshold for tone detection
        # The tone must be significantly louder than the background noise to be detected.
        threshold = noise_level * threshold_ratio

        # 6. Detect tone presence (create a boolean array where True indicates tone presence)
        tone_present = target_energy > threshold

        
        
        # If no part of the audio exceeds the threshold, no tone is detected
        if not np.any(tone_present):
            print(f"No sync tone detected above threshold (threshold={threshold:.2f}). Max energy at {target_freq}Hz: {np.max(target_energy):.2f}")
            return None, None

        # 7. Find contiguous segments of tone presence
        segments = []
        current_start_frame = -1

        # Iterate through the boolean array to find start and end frames of continuous True blocks
        for i, is_present in enumerate(tone_present):
            if is_present and current_start_frame == -1:
                # Tone starts here
                current_start_frame = i
            elif not is_present and current_start_frame != -1:
                # Tone ends here
                segments.append((current_start_frame, i - 1))
                current_start_frame = -1
        
        # Handle the case where the tone extends to the very end of the audio
        if current_start_frame != -1:
            segments.append((current_start_frame, len(tone_present) - 1))

        # If somehow no segments were found despite np.any(tone_present) being true (e.g., single frame),
        # this check handles it.
        if not segments:
            print("Error: Tone present but no continuous segments found after processing.")
            return None, None

        # 8. Find the longest segment (assuming the sync tone is the most prominent/longest one)
        longest_segment = max(segments, key=lambda s: s[1] - s[0])
        start_frame, end_frame = longest_segment

        # 9. Convert frames (STFT time bins) to actual time in milliseconds
        start_time_ms = librosa.frames_to_time(start_frame, sr=sr, hop_length=hop_length) * 1000
        end_time_ms = librosa.frames_to_time(end_frame, sr=sr, hop_length=hop_length) * 1000

        return start_time_ms, end_time_ms




    

    @staticmethod
    def save_keystroke_audio(keypress_samples, y, sr, session_id):
        os.makedirs(f"SessionsData/KeystrokeData/session_{session_id}", exist_ok=True)
        
        # Re-establish database connection
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        for start, end, key, key_id in keypress_samples:
            if key == '/':
                key = 'Forward slash'
            segment = y[start:end]
            filename = f"key_{key_id}_{key}.wav"
            filepath = f"SessionsData/KeystrokeData/session_{session_id}/{filename}"
            sf.write(filepath, segment, sr, subtype='PCM_16')
            print(filepath)
            # Update database
            cursor.execute("""
                UPDATE "KeyPresses"
                SET "AudioFileName" = %s
                WHERE "KeyID" = %s
            """, (filepath, key_id))
        
        conn.commit()
        conn.close()


    

    @staticmethod
    def cleanTheAudioSegment(y, sr, lastNumberOfSeconds):
        noise_profile = y[-int(lastNumberOfSeconds * sr):]  # Use the last 500 ms as the noise profile
        y_cleaned = nr.reduce_noise(y=y, y_noise=noise_profile, sr=sr)
        return y_cleaned
    
    
    

    @staticmethod
    def TrimAudioFromBeginning(y, trim_ms, sr):
        # --- Trim the first 80 ms of audio ---
        # param is Time to remove from the start (in ms)
        trim_samples = int(trim_ms * sr / 1000)  # Convert ms to samples

        # Remove the first 60 ms from the audio
        y_trimmed = y[trim_samples:]  # New audio starts after 60 ms

        # Update audio duration (now shorter by 60 ms)
        return y_trimmed

    

class PreProcessKeystrokeSensor:
    @staticmethod
    def save_keystroke_sensor(keypresses, df, session_id):
        output_folder = f"SessionsData/KeystrokeData/session_{session_id}"
        os.makedirs(output_folder, exist_ok=True)

        # Convert sensor DataFrame timestamp column to integers (if not already)
        df['timestamp'] = df['timestamp'].astype(int)

        # Reopen DB connection for updates
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()

        # Iterate over each keystroke and extract corresponding sensor data
        for keydown_ts, keyup_ts, key, key_id in keypresses:
            # Extract sensor data between keydown and keyup
            segment = df[(df['timestamp'] >= (keydown_ts - 15)) & (df['timestamp'] <= (keyup_ts + 15))]
            
            # Save to file
            filename = f"{output_folder}/sensor_{key_id}.csv"
            segment.to_csv(filename, index=False, header=False)

            # Update DB with filename
            update_query = """
            UPDATE "KeyPresses"
            SET "SensorFileName" = %s
            WHERE "KeyID" = %s
            """
            cursor.execute(update_query, (filename, key_id))

        # Commit changes and close DB
        conn.commit()
        conn.close()


