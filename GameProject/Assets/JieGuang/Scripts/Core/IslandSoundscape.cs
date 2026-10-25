using UnityEngine;

namespace JieGuang
{
    // Original synthesized recordings; see art/audio/generate_jieguang_v2.py.
    // Ambient sources are stereo beds; the balance follows the listener around the island.
    public sealed class IslandSoundscape : MonoBehaviour
    {
        AudioSource sea, wind, insects, theme, effects;
        AudioClip turn, shade, solved;
        Transform listener;
        Vector3 pier;
        Chapter chapter;

        public void Setup(Transform ears, Vector3 shoreline)
        {
            listener = ears;
            pier = shoreline;
            sea = Loop("SeaWavesV2", .13f);
            wind = Loop("IslandWindV2", .055f);
            insects = Loop("NightInsectsV2", .06f);
            theme = Loop("BorrowedLightThemeV2", .19f);
            effects = gameObject.AddComponent<AudioSource>();
            effects.playOnAwake = false;
            effects.spatialBlend = 0f;
            turn = Resources.Load<AudioClip>("Audio/LampTurnV2");
            shade = Resources.Load<AudioClip>("Audio/ShieldSwapV2");
            solved = Resources.Load<AudioClip>("Audio/PuzzleSolvedV2");
        }

        AudioSource Loop(string clip, float volume)
        {
            var source = gameObject.AddComponent<AudioSource>();
            source.playOnAwake = false;
            source.clip = Resources.Load<AudioClip>("Audio/" + clip);
            source.loop = true;
            source.volume = volume;
            source.spatialBlend = 0f;
            if (source.clip != null) source.Play();
            return source;
        }

        public void SetChapter(Chapter c) => chapter = c;
        public void LampTurn(bool changedShade) => OneShot(changedShade ? shade : turn, .35f);
        public void PuzzleSolved() => OneShot(solved, .4f);
        void OneShot(AudioClip clip, float gain) { if (clip != null) effects.PlayOneShot(clip, gain); }

        void Update()
        {
            if (listener == null || sea == null) return;
            Vector3 d = listener.position - pier;
            d.y = 0f;
            float inland = Mathf.Clamp01(d.magnitude / 38f);
            float dt = Time.unscaledDeltaTime;
            sea.volume = Mathf.MoveTowards(sea.volume, Mathf.Lerp(.16f, .065f, inland), dt * .035f);
            insects.volume = Mathf.MoveTowards(insects.volume, Mathf.Lerp(.025f, .075f, inland), dt * .025f);
            float musicLevel = chapter == Chapter.Interlude ? .10f : chapter >= Chapter.Finale ? .21f : .17f;
            if (Time.timeScale == 0f) musicLevel *= .65f;
            theme.volume = Mathf.MoveTowards(theme.volume, musicLevel, dt * .04f);
        }
    }
}
