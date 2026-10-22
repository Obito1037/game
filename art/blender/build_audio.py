"""Original synthesized score and lantern chime; generated locally, no samples."""
import json, math, wave
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "art/generated/audio"
OUT.mkdir(parents=True, exist_ok=True)
RATE=22050
DURATION=48
N=RATE*DURATION
score=np.zeros((N,2),dtype=np.float64)

def hz(note): return 440*2**((note-69)/12)
def add_circular(start, signal, pan=0):
    ix=(np.arange(len(signal))+int(start*RATE))%N
    score[ix,0]+=signal*math.sqrt((1-pan)/2)
    score[ix,1]+=signal*math.sqrt((1+pan)/2)

chords=[(50,57,62,66),(47,54,59,62),(43,50,55,59),(45,52,57,61)]
for c,chord in enumerate(chords):
    tt=np.arange(RATE*14)/RATE
    env=np.sin(np.minimum(tt/14,1)*np.pi)**1.6
    for j,note in enumerate(chord):
        sound=(np.sin(2*np.pi*hz(note)*tt+.015*np.sin(tt*.7))+.24*np.sin(2*np.pi*hz(note)*2*tt))*.038*env
        add_circular(c*12,sound,(j-1.5)*.18)
melody=[(0,74),(4,78),(8,81),(12,78),(16,74),(20,73),(24,71),(28,74),(32,78),(36,76),(40,73),(44,69)]
for k,(start,note) in enumerate(melody):
    tt=np.arange(RATE*8)/RATE
    env=(1-np.exp(-tt*90))*np.exp(-tt*.75)
    sound=(np.sin(2*np.pi*hz(note)*tt)+.25*np.sin(2*np.pi*hz(note)*2.002*tt)+.10*np.sin(2*np.pi*hz(note)*3.01*tt))*.09*env
    add_circular(start,sound,math.sin(k*1.7)*.65)
for sec,gain in [(.19,.16),(.43,.14),(.79,.10),(1.17,.08)]:
    score+=np.roll(score,int(sec*RATE),axis=0)[:,::-1]*gain
score=np.tanh(score*1.3)

def write(name, sound):
    data=(np.clip(sound,-.95,.95)*32767).astype('<i2')
    with wave.open(str(OUT/name),'wb') as f:
        f.setnchannels(2 if data.ndim==2 else 1);f.setsampwidth(2);f.setframerate(RATE);f.writeframes(data.tobytes())

write('NightLetters.wav',score)
tt=np.arange(RATE*2)/RATE
chime=(np.sin(2*np.pi*880*tt)+.34*np.sin(2*np.pi*1764*tt)+.12*np.sin(2*np.pi*2648*tt))*.21*(1-np.exp(-tt*180))*np.exp(-tt*3.5)
write('LanternChime.wav',chime)
(OUT/'audio-manifest.json').write_text(json.dumps({'title':'Night Letters','durationSeconds':48,'sampleRate':RATE,'method':'Original mathematical additive synthesis; no third-party audio samples','tools':'Blender Python + NumPy','files':['NightLetters.wav','LanternChime.wav']},indent=2),encoding='utf8')
print('BORROWED_LIGHT_AUDIO_READY',OUT)
