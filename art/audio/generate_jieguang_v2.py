"""Original, deterministic synthesized audio for JieGuang. No downloaded samples.

Run with Blender's bundled Python (numpy). 16-bit stereo PCM, 22.05 kHz.
The circular synthesis/reverb keeps ambience and score loops continuous.
"""
from pathlib import Path
import hashlib
import json
import wave
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "GameProject/Assets/JieGuang/Resources/Audio"
REPORT = ROOT / "art/verification/game-v2-audio"
SR = 22050
RNG = np.random.default_rng(20261022)
records = []


def write(name, data, description, peak=.8):
    data = np.asarray(data, dtype=np.float64)
    if data.ndim == 1:
        data = np.column_stack([data, data])
    data -= data.mean(axis=0)
    data *= peak / max(np.abs(data).max(), 1e-8)
    pcm = np.round(data * 32767).astype('<i2')
    path = OUT / (name + '.wav')
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())
    meta = path.with_suffix('.wav.meta')
    if not meta.exists():
        guid = hashlib.md5(('jieguang-audio-v2:'+name).encode()).hexdigest()
        meta.write_text(f'''fileFormatVersion: 2
guid: {guid}
AudioImporter:
  externalObjects: {{}}
  serializedVersion: 8
  defaultSettings:
    serializedVersion: 2
    loadType: 0
    sampleRateSetting: 0
    sampleRateOverride: 22050
    compressionFormat: 1
    quality: 0.65
    conversionMode: 0
    preloadAudioData: 1
  platformSettingOverrides: {{}}
  forceToMono: 0
  normalize: 0
  loadInBackground: 1
  ambisonic: 0
  3D: 1
  userData: Original deterministic synthesized audio; see art/audio/generate_jieguang_v2.py
  assetBundleName:
  assetBundleVariant:
''', encoding='utf-8')
    records.append(dict(name=name, description=description, duration=len(data)/SR,
                        peak=float(np.abs(data).max()), rms=float(np.sqrt(np.mean(data**2))),
                        seam_step=float(np.abs(data[-1]-data[0]).max()),
                        sha256=hashlib.sha256(path.read_bytes()).hexdigest()))


def noise(n, lo, hi):
    freq = np.fft.rfftfreq(n, 1/SR)
    shape = (1 - np.exp(-(freq/max(lo, 1))**2)) * np.exp(-(freq/hi)**2)
    spec = np.fft.rfft(RNG.standard_normal(n)) * shape
    result = np.fft.irfft(spec, n=n)
    return result/max(result.std(), 1e-8)


def ambience():
    n = SR*32
    t = np.arange(n)/SR
    surf = []
    wind = []
    bugs = []
    for side in range(2):
        swell = (.5 + .5*np.sin(2*np.pi*t/8 + side*.22))**2
        foam = (.5 + .5*np.sin(2*np.pi*t/8 - .6 + side*.22))**4
        surf.append(noise(n, 100, 1100)*(.18+.43*swell) + noise(n, 800, 4200)*foam*.22)
        gust = .3 + .18*np.sin(2*np.pi*t/16+side*.4) + .1*np.sin(2*np.pi*t/8)
        wind.append(noise(n, 70, 650)*gust)
        chirp = np.zeros(n)
        # Sparse alternating insects, each a small grouped pulse rather than a continuous whistle.
        for at in [1.7, 4.5, 9.4, 14.8, 19.2, 23.6, 28.3]:
            at += side*.65
            start = int(at*SR)
            ct = np.arange(int(.68*SR))/SR
            envelope = np.sin(np.pi*ct/.68)**2 * np.maximum(0, np.sin(2*np.pi*19*ct))**4
            freq = 2400+RNG.uniform(-180,180)
            tone = np.sin(2*np.pi*freq*ct + .3*np.sin(2*np.pi*45*ct))
            chirp[start:start+len(ct)] += tone*envelope
        bugs.append(chirp)
    write('SeaWavesV2', np.column_stack(surf), '32秒合成海浪，低频涌浪与后沿泡沫分层；可无缝循环', .68)
    write('IslandWindV2', np.column_stack(wind), '32秒合成海风，低通噪声与缓慢阵风；可无缝循环', .55)
    write('NightInsectsV2', np.column_stack(bugs), '32秒合成夜虫，疏密交替的脉冲虫鸣；可无缝循环', .4)


def hz(midi):
    return 440*2**((midi-69)/12)


def pluck(note, duration, soft=False):
    t = np.arange(round(duration*SR))/SR
    f = hz(note)
    y = np.zeros_like(t)
    for h, a in [(1,1), (2,.32), (3,.12), (4,.04)]:
        y += a*np.sin(2*np.pi*f*h*t)*np.exp(-t*(1.5+h*.55))
    y *= 1-np.exp(-t*90)
    y *= np.clip((duration-t)/.08,0,1)
    return y


def add(target, mono, start, gain, pan):
    indices = (int(round(start*SR)) + np.arange(len(mono))) % len(target)
    target[indices,0] += mono*gain*np.sqrt((1-pan)/2)
    target[indices,1] += mono*gain*np.sqrt((1+pan)/2)


def score():
    beat = 60/72
    duration = 64*beat
    song = np.zeros((round(duration*SR),2))
    chords = [(48,55,62,64),(45,52,59,60),(41,48,55,57),(43,50,57,60)]
    melody = [[72,76,79,76],[74,72,69,67],[69,72,76,74],[71,67,69,67],
              [72,76,79,84],[81,79,76,72],[74,77,76,72],[71,74,72,67],
              [76,79,84,79],[81,76,72,69],[77,76,74,72],[74,71,67,69],
              [72,76,79,76],[74,72,69,67],[69,72,76,74],[71,67,64,67]]
    for bar in range(16):
        chord = chords[bar%4]
        start = bar*4*beat
        # Warm felt-key arpeggio, low root and a restrained four-note melody.
        add(song, pluck(chord[0]-12, 4*beat), start, .24, -.08)
        for k in range(8):
            add(song, pluck(chord[k%4]+12, 2.8), start+k*.5*beat, .12, -.35)
        for k,note in enumerate(melody[bar]):
            add(song, pluck(note, 3.2), start+(k+.08)*beat, .21 if k==0 else .16, .26)
        padt=np.arange(round(5*beat*SR))/SR
        env=np.sin(np.pi*np.clip(padt/(5*beat),0,1))**2
        pad=sum(np.sin(2*np.pi*hz(note)*padt)+.1*np.sin(2*np.pi*hz(note)*2*padt) for note in chord)
        add(song,pad*env,start,.018,0)
    dry=song.copy()
    for delay,gain in [(.19,.12),(.37,.10),(.61,.07),(1.03,.05)]:
        song += np.roll(dry[:,::-1],int(delay*SR),axis=0)*gain
    write('BorrowedLightThemeV2',song,'原创53.33秒主题：72 BPM，C/Am/F/G和声，毡音拨奏及柔和长音；循环尾音回卷',.76)


def effects():
    n=int(.22*SR); t=np.arange(n)/SR
    turn=noise(n,400,4300)*np.exp(-t*42)*.12 + np.sin(2*np.pi*340*t)*np.exp(-t*24)*.45
    turn*=np.minimum(t/.003,1)*np.minimum((.22-t)/.02,1)
    write('LampTurnV2',turn,'柔和的铜轴转动轻响',.48)
    n=int(.4*SR); t=np.arange(n)/SR
    shade=(np.sin(2*np.pi*510*t)+.24*np.sin(2*np.pi*1175*t))*np.exp(-t*15)
    shade*=np.minimum(t/.003,1)*np.minimum((.4-t)/.04,1)
    write('ShieldSwapV2',shade,'铜灯罩扣合的短促双泛音',.48)
    success=np.zeros((SR*3,2))
    for i,note in enumerate([72,76,79]): add(success,pluck(note,2.2),i*.18,.28,(i-1)*.3)
    write('PuzzleSolvedV2',success,'C大调三音的解谜确认声',.6)


if __name__ == '__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    REPORT.mkdir(parents=True,exist_ok=True)
    ambience(); score(); effects()
    report=dict(method='Original deterministic procedural synthesis; no external recordings or music used.',
                seed=20261022,sample_rate=SR,channels=2,bits=16,files=records,
                validation='Numerical peak/RMS/seam checks only. In-game listening and WebGL autoplay remain manual QA.')
    (REPORT/'audio-generation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(records,ensure_ascii=False,indent=2))
