import time
import queue
import threading
import warnings
import re
import pyaudio
import numpy as np
from openai import OpenAI

TI_REGEX = re.compile(r'(?<![stx])ti([aeiouàèéìòù])')
H_REGEX = re.compile(r'\bh')

def latin_to_italian_phonetics(text):
    text = text.lower()
    replacements = {"mihi": "michi", "nihil": "nichil", "ae": "e", "oe": "e", "ph": "f", "th": "t", "x": "cs", "y": "i"}
    for old, new in replacements.items(): text = text.replace(old, new)
    text = TI_REGEX.sub(r'zi\1', text)
    text = H_REGEX.sub('', text)
    return text

def apply_reverb(audio_np, sample_rate=24000, delay_ms=100, decay=0.5):
    delay_samples = int(sample_rate * (delay_ms / 1000.0))
    audio_float = audio_np.astype(np.float32)
    reverb_audio = np.zeros(len(audio_float) + delay_samples, dtype=np.float32)
    reverb_audio[:len(audio_float)] = audio_float
    reverb_audio[delay_samples:] += audio_float * decay
    return np.clip(reverb_audio, -32768, 32767).astype(np.int16)

class Ap:
    def __init__(self, params=None):
        self.params = params or {}
        self.samplerate = self.params.get("samplerate", 24000)
        self.buffer_size = self.params.get("buffer_size", 960)
        self.channels = self.params.get("channels", 1)
        self.sample_format = pyaudio.paInt16
        self.audio_queue = queue.Queue()
        self._playback_buffer = bytearray()
        self.finished_event = threading.Event()
        self.finished_event.set()
        self.is_playing = False
        p = pyaudio.PyAudio()
        self.stream = p.open(
            format=self.sample_format, channels=self.channels, rate=self.samplerate,
            frames_per_buffer=self.buffer_size, output=True, stream_callback=self._callback,
        )

    def _callback(self, in_data, frame_count, time_info, status):
        expected_bytes = frame_count * self.channels * pyaudio.get_sample_size(self.sample_format)
        while len(self._playback_buffer) < expected_bytes:
            try:
                chunk = self.audio_queue.get_nowait()
                self._playback_buffer.extend(chunk)
                self.is_playing = True
            except queue.Empty:
                break
        if len(self._playback_buffer) >= expected_bytes:
            data = bytes(self._playback_buffer[:expected_bytes])
            del self._playback_buffer[:expected_bytes]
        else:
            data = bytes(self._playback_buffer) + b'\x00' * (expected_bytes - len(self._playback_buffer))
            self._playback_buffer.clear()
            if self.is_playing:
                self.is_playing = False
                self.finished_event.set()
        return (data, pyaudio.paContinue)

    def clear_queue(self):
        with self.audio_queue.mutex: self.audio_queue.queue.clear()
        self._playback_buffer.clear()
        self.is_playing = False
        self.finished_event.set()
        
    def play_sound(self, sound):
        self.finished_event.clear()
        sound_bytes = sound.tobytes() if isinstance(sound, np.ndarray) else sound
        chunk_bytes_len = self.buffer_size * pyaudio.get_sample_size(self.sample_format) * self.channels
        for i in range(0, len(sound_bytes), chunk_bytes_len):
            chunk = sound_bytes[i : i + chunk_bytes_len]
            self.audio_queue.put(chunk)

    def close(self):
        self.is_playing = False
        self.finished_event.set()
        if hasattr(self, 'stream') and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()

class Tts:
    def __init__(self, params=None):
        self.params = params or {}
        self.base_url = self.params.get("base_url", "http://localhost:8880/v1")
        self.model_name = self.params.get("model_name", "kokoro")
        self.voice = self.params.get("voice", "if_sara")
        warnings.filterwarnings("ignore", module="TTS")
        self.client = OpenAI(base_url=self.base_url, api_key="empty") if self.base_url else OpenAI()

    def run_tts_sync(self, ap, data, app_state, display_text=None):
        try:
            response = self.client.audio.speech.create(
                voice=self.voice, input=data, model=self.model_name, response_format="pcm", speed=0.80
            )
            audio_content = response.content
            valid_len = (len(audio_content) // 2) * 2
            audio_np = np.frombuffer(audio_content[:valid_len], dtype=np.int16)
            audio_np = apply_reverb(audio_np)
            if display_text:
                app_state.set_subtitle(display_text)
            ap.play_sound(audio_np)
            while not ap.finished_event.wait(timeout=0.05):
                if app_state.skip_requested or app_state.repeat_requested:
                    ap.clear_queue()
                    break
        except Exception as e:
            pass

def thread_audio_lettura(ap, tts, stop_event, idle_duration, frasi_list, app_state):
    if not frasi_list:
        stop_event.set()
        return
    pausa_calcolata = max(4.0, idle_duration + 1.5) 
    idx = 0
    while idx < len(frasi_list):
        if stop_event.is_set(): break 
        app_state.progress = (idx) / len(frasi_list)
        app_state.skip_requested = False
        app_state.repeat_requested = False
        frase_lat = frasi_list[idx]
        frase_ita = latin_to_italian_phonetics(frase_lat)
        print(f"\nOriginale: {frase_lat}")
        print(f"Fonetica:  {frase_ita}")
        tts.run_tts_sync(ap, frase_ita, app_state, display_text=frase_lat)
        app_state.set_subtitle("") 
        if app_state.repeat_requested: continue
        if app_state.skip_requested:
            idx += 1
            continue
        end_time = time.time() + pausa_calcolata
        interrotto = False
        while time.time() < end_time:
            if stop_event.is_set() or app_state.skip_requested or app_state.repeat_requested:
                interrotto = True
                break
            time.sleep(0.05)
        if interrotto:
            if app_state.repeat_requested: continue
            if app_state.skip_requested:
                idx += 1
                continue
            break 
        idx += 1
    app_state.progress = 1.0 
    time.sleep(3)
    stop_event.set()