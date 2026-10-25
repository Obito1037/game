"""Builds the review-video music bed from the game's own audio (no new assets):
theme and NightLetters alternate with 3 s crossfades over a quiet bed of sea waves and night
insects. 44.1 kHz stereo 16-bit, 12 minutes; the recorder writes exactly the video's length and
fades out at the end card.

  python -I tools/make_review_soundtrack.py <audio dir> <out.wav>
"""
import sys, wave
import numpy as np

SR = 44100


def load(path):
    with wave.open(path, 'rb') as w:
        ch, rate, n = w.getnchannels(), w.getframerate(), w.getnframes()
        data = np.frombuffer(w.readframes(n), dtype=np.int16).astype(np.float32) / 32768.0
    data = data.reshape(-1, ch)
    if ch == 1:
        data = np.repeat(data, 2, axis=1)
    # resample to 44.1 kHz (linear interpolation is enough for a music bed)
    t_src = np.arange(len(data)) / rate
    t_dst = np.arange(int(len(data) * SR / rate)) / SR
    return np.stack([np.interp(t_dst, t_src, data[:, c]) for c in range(2)], axis=1).astype(np.float32)


def loop_to(clip, n, fade=SR * 2):
    out = np.zeros((n, 2), np.float32)
    pos = 0
    ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
    while pos < n:
        seg = clip.copy()
        seg[:fade] *= ramp
        seg[-fade:] *= ramp[::-1]
        end = min(n, pos + len(seg))
        out[pos:end] += seg[:end - pos]
        pos += len(seg) - fade
    return out


def main(audio_dir, out_path):
    theme = load(audio_dir + '/BorrowedLightThemeV2.wav')
    letters = load(audio_dir + '/NightLetters.wav')
    sea = load(audio_dir + '/SeaWavesV2.wav')
    insects = load(audio_dir + '/NightInsectsV2.wav')
    total = SR * 60 * 12
    music = np.zeros((total, 2), np.float32)
    xf = SR * 3
    ramp = np.linspace(0, 1, xf, dtype=np.float32)[:, None]
    pos, i = 0, 0
    while pos < total:
        seg = (theme if i % 2 == 0 else letters).copy()
        seg[:xf] *= ramp
        seg[-xf:] *= ramp[::-1]
        end = min(total, pos + len(seg))
        music[pos:end] += seg[:end - pos]
        pos += len(seg) - xf
        i += 1
    mix = music * 0.85 + loop_to(sea, total) * 0.16 + loop_to(insects, total) * 0.06
    # gentle 4 s fade-in; the recorder fades out at the end card
    mix[:SR * 4] *= np.linspace(0, 1, SR * 4, dtype=np.float32)[:, None]
    peak = np.max(np.abs(mix))
    mix *= 0.89 / max(peak, 1e-6)
    pcm = (np.clip(mix, -1, 1) * 32767).astype(np.int16)
    with wave.open(out_path, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print('wrote', out_path, round(total / SR), 's')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
