import os
import cv2
import numpy as np
import threading
import pygame
from core.audio_engine import Ap, Tts, thread_audio_lettura

class AppState:
    def __init__(self):
        self.current_subtitle = ""
        self.cached_lines = []  
        self.skip_requested = False
        self.repeat_requested = False
        self.max_text_width = 960 
        self.progress = 0.0
        self.subtitle_alpha = 0.0
        self.subtitle_target_alpha = 0.0
        self.curr_video_state = "idle"
        self.prev_video_state = "idle"
        self.transition_frames = 15
        self.transition_counter = 0
        self.music_volume = 0.6
        self.music_target_volume = 0.6
        self.osd_message = ""
        self.osd_timer = 0
        self.rotation_idx = 1

    def trigger_osd(self, message, frames=45):
        self.osd_message = message
        self.osd_timer = frames

    def set_subtitle(self, text):
        if text:
            self.current_subtitle = text
            self.cached_lines = self._calculate_text_wrap(text, self.max_text_width)
            self.subtitle_target_alpha = 1.0 
        else:
            self.subtitle_target_alpha = 0.0 

    def _calculate_text_wrap(self, text, max_width):
        font, scale, thickness = cv2.FONT_HERSHEY_COMPLEX, 0.55, 1
        words = text.split()
        lines, current_line = [], ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            size, _ = cv2.getTextSize(test_line, font, scale, thickness)
            if size[0] <= max_width: current_line = test_line
            else:
                if current_line: lines.append(current_line); current_line = word
                else: lines.append(word); current_line = ""
        if current_line: lines.append(current_line)
        return lines

def draw_ui_elements(img, app_state):
    if app_state.cached_lines and app_state.subtitle_alpha > 0.01:
        font, scale, thickness = cv2.FONT_HERSHEY_COMPLEX, 0.55, 1
        color_text, color_outline, line_spacing = (255, 255, 255), (0, 0, 0), 10
        max_line_height = max([cv2.getTextSize(line, font, scale, thickness)[0][1] for line in app_state.cached_lines])
        total_text_height = (len(app_state.cached_lines) * max_line_height) + ((len(app_state.cached_lines) - 1) * line_spacing)
        padding = 20
        box_y_start = max(0, img.shape[0] - total_text_height - (padding * 2) - 40)
        target_look = img.copy()
        box_overlay = target_look.copy()
        cv2.rectangle(box_overlay, (0, box_y_start), (img.shape[1], img.shape[0]), (10, 10, 15), -1)
        cv2.line(box_overlay, (0, box_y_start), (img.shape[1], box_y_start), (255, 240, 0), 2)
        cv2.addWeighted(box_overlay, 0.85, target_look, 0.15, 0, target_look)
        y_current = box_y_start + padding + max_line_height
        for line in app_state.cached_lines:
            size, _ = cv2.getTextSize(line, font, scale, thickness)
            x = max(10, int((img.shape[1] - size[0]) / 2)) 
            cv2.putText(target_look, line, (x + 1, y_current + 1), font, scale, color_outline, thickness + 1, cv2.LINE_AA)
            cv2.putText(target_look, line, (x, y_current), font, scale, color_text, thickness, cv2.LINE_AA)
            y_current += max_line_height + line_spacing
        cv2.addWeighted(target_look, app_state.subtitle_alpha, img, 1 - app_state.subtitle_alpha, 0, img)
    if app_state.progress > 0:
        bar_height = 4
        bar_y = img.shape[0] - bar_height
        cv2.rectangle(img, (0, bar_y), (img.shape[1], img.shape[0]), (30, 30, 30), -1)
        bar_width = int(img.shape[1] * app_state.progress)
        cv2.rectangle(img, (0, bar_y), (bar_width, img.shape[0]), (255, 240, 0), -1)
    if app_state.osd_timer > 0:
        font_osd = cv2.FONT_HERSHEY_DUPLEX
        osd_text = app_state.osd_message
        osd_size, _ = cv2.getTextSize(osd_text, font_osd, 0.6, 1) 
        osd_x = img.shape[1] - osd_size[0] - 30
        osd_y = 40
        cv2.rectangle(img, (osd_x - 10, osd_y - osd_size[1] - 10), (osd_x + osd_size[0] + 10, osd_y + 10), (0, 0, 0), -1)
        cv2.putText(img, osd_text, (osd_x, osd_y), font_osd, 0.6, (255, 240, 0), 1, cv2.LINE_AA)
        app_state.osd_timer -= 1

def preload_video(video_path, target_width, target_height):
    cap = cv2.VideoCapture(video_path)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret: break
        frames.append(cv2.resize(frame, (target_width, target_height)))
    cap.release()
    return frames

def get_ping_pong_frame(frames_list, state_dict, video_key):
    if not frames_list: return None
    idx = state_dict[video_key]['idx']
    direction = state_dict[video_key]['dir']
    frame = frames_list[idx]
    idx += direction
    if idx >= len(frames_list) - 1:
        idx = len(frames_list) - 1
        state_dict[video_key]['dir'] = -1
    elif idx <= 0:
        idx = 0
        state_dict[video_key]['dir'] = 1
    state_dict[video_key]['idx'] = idx
    return frame

def run_goddess_app(video_talk_path, video_idle_path, audio_music_path, frasi_list, voce_tts="if_sara"):
    app_state = AppState()
    pygame.mixer.init()
    if os.path.exists(audio_music_path):
        pygame.mixer.music.load(audio_music_path)
        pygame.mixer.music.set_volume(app_state.music_volume)
        pygame.mixer.music.play(loops=-1, fade_ms=2000)
    ap = Ap()
    tts = Tts({"voice": voce_tts}) 
    stop_event = threading.Event()
    cap_talk = cv2.VideoCapture(video_talk_path)
    if not cap_talk.isOpened(): return
    fps = cap_talk.get(cv2.CAP_PROP_FPS) or 25 
    delay = int(1000 / fps)
    target_width = int(cap_talk.get(cv2.CAP_PROP_FRAME_WIDTH))
    target_height = int(cap_talk.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap_talk.release()
    frames_talk = preload_video(video_talk_path, target_width, target_height)
    frames_idle = preload_video(video_idle_path, target_width, target_height)
    if not frames_idle: frames_idle = frames_talk
    idle_duration = len(frames_idle) / (fps if fps > 0 else 25)
    audio_thread = threading.Thread(target=thread_audio_lettura, args=(ap, tts, stop_event, idle_duration, frasi_list, app_state))
    audio_thread.daemon = True 
    audio_thread.start()
    window_name = "Dea/Dio Runtime"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    curr_w = target_height if app_state.rotation_idx in [1, 3] else target_width
    curr_h = target_width if app_state.rotation_idx in [1, 3] else target_height
    if curr_h > curr_w:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, curr_w, curr_h)
    else:
        cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    app_state.max_text_width = target_width - 80 
    video_states = {"talk": {"idx": 0, "dir": 1}, "idle": {"idx": 0, "dir": 1}}
    rotations = [None, cv2.ROTATE_90_COUNTERCLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_CLOCKWISE]
    while not stop_event.is_set():
        if cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            stop_event.set()
            break
        if app_state.subtitle_alpha < app_state.subtitle_target_alpha:
            app_state.subtitle_alpha = min(1.0, app_state.subtitle_alpha + 0.15) 
        elif app_state.subtitle_alpha > app_state.subtitle_target_alpha:
            app_state.subtitle_alpha = max(0.0, app_state.subtitle_alpha - 0.15) 
            if app_state.subtitle_alpha <= 0.01: app_state.cached_lines = []
        target_video_state = "talk" if ap.is_playing else "idle"
        app_state.music_target_volume = 0.08 if ap.is_playing else 0.60 
        if abs(app_state.music_volume - app_state.music_target_volume) > 0.01:
            app_state.music_volume += 0.01 if app_state.music_volume < app_state.music_target_volume else -0.05
            app_state.music_volume = max(0.0, min(1.0, app_state.music_volume))
            if pygame.mixer.get_init(): pygame.mixer.music.set_volume(app_state.music_volume)
        if target_video_state != app_state.curr_video_state:
            app_state.prev_video_state, app_state.curr_video_state = app_state.curr_video_state, target_video_state
            app_state.transition_counter = app_state.transition_frames
        active_frames = frames_talk if app_state.curr_video_state == "talk" else frames_idle
        frame_curr = get_ping_pong_frame(active_frames, video_states, app_state.curr_video_state)
        if frame_curr is not None:
            frame_render = frame_curr.copy()
            if app_state.transition_counter > 0:
                prev_frames = frames_talk if app_state.prev_video_state == "talk" else frames_idle
                frame_prev = get_ping_pong_frame(prev_frames, video_states, app_state.prev_video_state)
                if frame_prev is not None:
                    alpha_curr = 1.0 - (app_state.transition_counter / app_state.transition_frames)
                    frame_render = cv2.addWeighted(frame_render, alpha_curr, frame_prev, 1.0 - alpha_curr, 0)
                app_state.transition_counter -= 1
            draw_ui_elements(frame_render, app_state)
            current_rotation = rotations[app_state.rotation_idx]
            if current_rotation is not None:
                frame_render = cv2.rotate(frame_render, current_rotation)
            cv2.imshow(window_name, frame_render)
        key = cv2.waitKey(delay) & 0xFF
        if key == ord('q') or key == 27 or key == ord('Q'): 
            stop_event.set()
        elif key == ord('n') or key == ord('N'): 
            app_state.skip_requested = True
            app_state.trigger_osd(">> SALTO FRASE...", frames=40)
        elif key == ord('r') or key == ord('R'): 
            app_state.repeat_requested = True
            app_state.trigger_osd("<< RIPETO FRASE...", frames=40)
        elif key == ord(' '): 
            app_state.rotation_idx = (app_state.rotation_idx + 1) % 4
            curr_w = target_height if app_state.rotation_idx in [1, 3] else target_width
            curr_h = target_width if app_state.rotation_idx in [1, 3] else target_height
            if curr_h > curr_w:
                cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_NORMAL)
                cv2.resizeWindow(window_name, curr_w, curr_h)
            else:
                cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            app_state.trigger_osd("ROTAZIONE VIDEO...", frames=40)
    cv2.destroyAllWindows()
    ap.close()
    if pygame.mixer.get_init():
        pygame.mixer.music.fadeout(1000)
        pygame.time.wait(1000)
        pygame.quit()