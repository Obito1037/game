using System.Collections.Generic;
using UnityEngine;
using UnityEngine.InputSystem;

namespace JieGuang
{
    // Keyboard reads go through here so automated QA can inject presses (Queue) and held keys
    // (Hold) while the Editor window is in the background; real input works unchanged.
    public static class GameInput
    {
        static readonly HashSet<Key> queued = new HashSet<Key>();
        static readonly HashSet<Key> thisFrame = new HashSet<Key>();
        static readonly Dictionary<Key, float> held = new Dictionary<Key, float>();
        static int frame = -1;

        public static void Queue(Key k) => queued.Add(k);
        public static void Hold(Key k, float seconds) => held[k] = Time.unscaledTime + seconds;

        static void Roll()
        {
            if (Time.frameCount == frame) return;
            frame = Time.frameCount;
            thisFrame.Clear();
            thisFrame.UnionWith(queued);
            queued.Clear();
        }

        public static bool Down(Key k)
        {
            Roll();
            var kb = Keyboard.current;
            return (kb != null && kb[k].wasPressedThisFrame) || thisFrame.Contains(k);
        }

        public static bool Held(Key k)
        {
            var kb = Keyboard.current;
            return (kb != null && kb[k].isPressed) || (held.TryGetValue(k, out float until) && Time.unscaledTime < until);
        }

        public static bool AnyDown(params Key[] keys)
        {
            foreach (var k in keys) if (Down(k)) return true;
            return false;
        }
    }
}
