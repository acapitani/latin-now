# LATINOW — Statua Animata

**LATINOW** is a Python-based software suite that allows you to animate virtual statues and make them speak dynamically.

The application integrates local Text-to-Speech (TTS) via an OpenAI-compatible API, real-time audio reverb processing, and a custom video engine (OpenCV) that smoothly transitions between "idle" and "talking" video loops while syncing with the generated audio. It is optimized for ecclesiastical Latin pronunciation with automatic phonetic correction.

---

## Project Structure

The project is driven by a unified application with two main operational phases:

### The Launcher (UI)

A graphical user interface developed with `tkinter` that allows you to:

- Select your preferred deity/statue from the available assets  
- Type or import the text phrases you want the statue to recite  
- Launch the projection  

### The Projection Engine (Runtime)

The execution environment that processes the text. It:

- Sends phrases to a local TTS server  
- Applies real-time audio reverb using `numpy` and `pyaudio`  
- Plays background music via `pygame`  
- Renders the visual projection (with subtitles and transitions) using `OpenCV`  

---

## System Requirements

- **Python 3.8+**
- **Backend Server:** WSL and Docker Desktop installed (Windows only, for Kokoro TTS backend)
- **Display:** Monitor or projector (supports vertical/portrait rotation)

---

## Installation & Environment Setup

### 1 — Clone the Repository

```bash
git clone https://github.com/acapitani/latin-now.git
cd latin-now
```

---

### 2 - Download assets resources

Download the assets from the following URL:

[https://drive.google.com/file/d/1iWNrl5g7oe2CODO5dkKZ2uS9JnHTRXLE/view?usp=sharing](https://drive.google.com/file/d/1iWNrl5g7oe2CODO5dkKZ2uS9JnHTRXLE/view?usp=sharing)

And unzip into the project folder.

---

### 3 — Create and Activate a Virtual Environment

It is highly recommended to use a virtual environment.

```bash
python -m venv venv
```

Activate it:

**Windows**
```bash
venv\Scripts\activate
```

**Linux / Mac**
```bash
source venv/bin/activate
```

---

### 4 — Install Dependencies

> Linux users may need system audio libraries before installing PyAudio:

```bash
sudo apt-get install portaudio19-dev python3-pyaudio
```

Then install Python dependencies:

```bash
pip install -r requirements.txt
```

---

### 5 — Start the Backend Service (TTS)

The application expects an OpenAI-compatible endpoint at:

```
http://localhost:8880/v1
```

Start Kokoro FastAPI with GPU support:

```bash
# Windows: run via WSL
wsl sudo docker run --rm --detach \
--gpus all \
-p 8880:8880 \
--name kokoro \
ghcr.io/remsky/kokoro-fastapi-gpu:latest
```

---

# Adding Custom Statues

You can expand the application by adding custom statues.

## Folder Structure

Inside:

```
assets/statue/
```

Choose the gender folder:

```
assets/statue/maschio/
assets/statue/femmina/
```

Create a folder named after your statue:

```
assets/statue/femmina/Diana/
```

Inside it, create exactly three subfolders:

```
audio/
frasi/
video/
```

---

## Required Files

- `audio/traccia.mp3` → Background soundtrack (looped during projection)
- `frasi/default.txt` → Default phrases file
- `video/idle.mp4` → Looping video when statue is not speaking
- `video/talk.mp4` → Looping video when statue is speaking

---

## Directory Example

```
assets/
└── statue/
    └── femmina/
        └── Diana/
            ├── audio/
            │   └── traccia.mp3
            ├── frasi/
            │   └── default.txt
            └── video/
                ├── idle.mp4
                └── talk.mp4
```

---

# Generating High-Quality Videos (AI Prompts)

To generate high-quality `idle.mp4` and `talk.mp4` files using AI video generators:

---

## Prompt for IDLE Video (Mouth Closed)

```
Vertical 9:16 aspect ratio. Cinematic close-up portrait of a living white marble classical statue of the goddess Diana. Framed specifically for a vertical screen, focusing on her head and upper torso. The composition includes significant negative space above her head, ensuring the top of the statue is positioned well below the upper edge of the frame. The statue is magically alive but resting. She is completely still, only breathing softly and blinking slowly. Serene, majestic expression. Divine ethereal lighting, pure black background. Ultra-realistic, 8k resolution. Perfectly static camera, absolutely no camera movement.
```

---

## Prompt for TALK Video (Mouth Moving)

```
Vertical 9:16 aspect ratio. Cinematic close-up portrait of a living white marble classical statue of the goddess Diana. Framed specifically for a vertical screen, focusing on her head and upper torso. Ensure significant negative space between the top of her head and the upper edge of the frame to avoid cropping. The statue is magically alive and actively talking, moving her lips continuously and expressively as if reciting a solemn ancient speech in Latin. Subtle, natural head movements while speaking. Divine ethereal lighting, pure black background. Ultra-realistic, 8k resolution. Perfectly static camera, absolutely no camera movement.
```

---

# Running LATINOW

Ensure the TTS backend is active, then launch:

```bash
# Make sure your virtual environment is activated
python main.py
```

---

## Quick Commands (Runtime)

While the projection is running:

- **Q** or **ESC** → Close projection and return to launcher  
- **N** → Skip to next phrase  
- **R** → Repeat current phrase  
- **SPACE** → Rotate video 90° (cycles through 4 orientations)  
