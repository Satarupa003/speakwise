"""
VisualAnalyzer
==============
Analyzes the visual track of a speech video frame by frame.

Uses OpenCV's built-in face/eye detection (Haar cascades) which works
out of the box without downloading any model files.

What it detects:
  1. Eye contact      — face centered and forward-facing
  2. Posture          — head position stability
  3. Gesture frequency — overall motion between frames
  4. Facial presence  — how consistently face is visible

Output dict shape:
{
    "eye_contact_score":      float,   # 0–100
    "gesture_frequency":      float,   # movements per minute
    "posture_score":          float,   # 0–100
    "facial_expression_data": dict,
    "frame_count":            int,
    "analyzed_frames":        int,
    "duration_seconds":       float,
    "eye_contact_timeline":   list,
    "gesture_timeline":       list,
    "posture_timeline":       list,
}
"""

import os
import cv2
import numpy as np
from pathlib import Path
from typing import Any

# Analyze 2 frames per second — enough for body language
ANALYSIS_FPS = 2

# Motion threshold — how much pixel change counts as movement
MOTION_THRESHOLD = 0.02


class VisualAnalyzer:

    def __init__(self):
        # OpenCV built-in Haar cascade classifiers — no download needed
        self._face_cascade = None
        self._eye_cascade = None

    # ── Public API ──────────────────────────────────────────────────────────

    async def analyze(self, video_path: str) -> dict[str, Any]:
        video_path = str(video_path)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        print(f"[VisualAnalyzer] Analyzing {Path(video_path).name}")
        self._init_detectors()

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video: {video_path}")

        try:
            result = self._process_video(cap)
        finally:
            cap.release()

        print(
            f"[VisualAnalyzer] ✓ Done — "
            f"eye contact: {result['eye_contact_score']:.0f}/100, "
            f"posture: {result['posture_score']:.0f}/100, "
            f"gestures: {result['gesture_frequency']:.1f}/min"
        )
        return result

    # ── Setup ───────────────────────────────────────────────────────────────

    def _init_detectors(self):
        """Load OpenCV Haar cascade classifiers (built into OpenCV)."""
        cv2_data = cv2.data.haarcascades
        self._face_cascade = cv2.CascadeClassifier(
            cv2_data + "haarcascade_frontalface_default.xml"
        )
        self._eye_cascade = cv2.CascadeClassifier(
            cv2_data + "haarcascade_eye.xml"
        )

    # ── Core processing ──────────────────────────────────────────────────────

    def _process_video(self, cap: cv2.VideoCapture) -> dict[str, Any]:
        video_fps     = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration      = total_frames / video_fps
        frame_interval = max(1, int(video_fps / ANALYSIS_FPS))

        eye_contact_results = []
        motion_results      = []
        posture_results     = []
        face_detected_count = 0

        eye_timeline     = []
        gesture_timeline = []
        posture_timeline = []

        prev_gray   = None
        frame_idx   = 0
        analyzed    = 0

        print(f"[VisualAnalyzer] {duration:.1f}s video, analyzing every "
              f"{frame_interval} frames ({ANALYSIS_FPS} FPS)")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % frame_interval == 0:
                timestamp = round(frame_idx / video_fps, 2)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

                # ── Face + eye detection ──────────────────────────────────
                faces = self._face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
                )
                face_found   = len(faces) > 0
                eye_contact  = False
                posture_score = 50.0

                if face_found:
                    face_detected_count += 1
                    eye_contact, posture_score = self._analyze_face(
                        gray, frame.shape, faces[0]
                    )

                eye_contact_results.append(eye_contact)
                posture_results.append(posture_score)

                eye_timeline.append({
                    "time": timestamp,
                    "looking_at_camera": eye_contact,
                    "face_detected": face_found,
                })
                posture_timeline.append({
                    "time": timestamp,
                    "posture_score": round(posture_score, 1),
                })

                # ── Motion detection (gesture proxy) ──────────────────────
                motion = 0.0
                if prev_gray is not None:
                    motion = self._detect_motion(prev_gray, gray)
                motion_results.append(motion)
                gesture_timeline.append({
                    "time": timestamp,
                    "hands_moving": motion > MOTION_THRESHOLD,
                })

                prev_gray = gray
                analyzed += 1

            frame_idx += 1

        # ── Aggregate ─────────────────────────────────────────────────────
        # Eye contact: % of frames where looking at camera
        # Bonus if face was consistently detected
        face_visibility = face_detected_count / max(analyzed, 1)
        raw_eye = (
            sum(eye_contact_results) / len(eye_contact_results)
            if eye_contact_results else 0.5
        )
        eye_contact_score = min(100.0, raw_eye * 100 * (0.5 + 0.5 * face_visibility))

        # Gesture frequency: motion events per minute
        moving_frames = sum(1 for m in motion_results if m > MOTION_THRESHOLD)
        gesture_frequency = (moving_frames / (duration / 60)) if duration > 0 else 0.0

        # Posture: average posture score across frames
        posture_avg = (
            float(np.mean(posture_results)) if posture_results else 50.0
        )

        # Facial expression placeholder (needs ML model for real detection)
        facial_expression_data = {
            "smile_ratio":   0.0,
            "neutral_ratio": face_visibility,
            "tense_ratio":   1.0 - face_visibility,
            "face_visibility": round(face_visibility, 3),
        }

        return {
            "eye_contact_score":      round(eye_contact_score, 1),
            "gesture_frequency":      round(gesture_frequency, 1),
            "posture_score":          round(posture_avg, 1),
            "facial_expression_data": facial_expression_data,
            "frame_count":            frame_idx,
            "analyzed_frames":        analyzed,
            "duration_seconds":       round(duration, 2),
            "eye_contact_timeline":   eye_timeline,
            "gesture_timeline":       gesture_timeline,
            "posture_timeline":       posture_timeline,
        }

    # ── Face analysis ────────────────────────────────────────────────────────

    def _analyze_face(
        self, gray: np.ndarray, frame_shape: tuple, face: np.ndarray
    ) -> tuple[bool, float]:
        """
        Given a detected face bounding box, estimate:
          - eye_contact: is the face centered in frame?
          - posture_score: is the head at a good vertical position?
        """
        x, y, w, h = face
        fh, fw = frame_shape[:2]

        # ── Eye contact: face should be centered horizontally ─────────────
        face_center_x = x + w / 2
        frame_center_x = fw / 2
        horizontal_offset = abs(face_center_x - frame_center_x) / fw
        # Also check face isn't too small (person too far away)
        face_size_ratio = w / fw
        eye_contact = horizontal_offset < 0.2 and face_size_ratio > 0.1

        # ── Posture: face should be in upper portion of frame ─────────────
        face_center_y = y + h / 2
        # Ideal: face in top 60% of frame
        vertical_position = face_center_y / fh
        if vertical_position < 0.6:
            posture_score = 90.0
        elif vertical_position < 0.75:
            posture_score = 70.0
        else:
            posture_score = 40.0  # face too low — slouching

        # Bonus if face is well-centered
        if horizontal_offset < 0.1:
            posture_score = min(100.0, posture_score + 10)

        return eye_contact, posture_score

    # ── Motion detection ─────────────────────────────────────────────────────

    def _detect_motion(self, prev: np.ndarray, curr: np.ndarray) -> float:
        """
        Estimate how much changed between two frames.
        Uses frame differencing — simple and fast.
        Returns normalized motion amount (0.0 – 1.0).
        """
        # Resize to small size for speed
        small_prev = cv2.resize(prev, (160, 90))
        small_curr = cv2.resize(curr, (160, 90))

        diff = cv2.absdiff(small_prev, small_curr)
        # Apply threshold to ignore noise
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        # Normalize by total pixels
        motion = np.sum(thresh) / (thresh.size * 255)
        return float(motion)
