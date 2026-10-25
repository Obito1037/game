using System.Collections.Generic;
using UnityEngine;

namespace JieGuang
{
    // Resolves the named anchors of Island.prefab (built by the environment track, see
    // setup/GPT6-协作提示词.md). Any anchor the prefab lacks is created at a graybox position,
    // and when no prefab is assigned at all a graybox island is built so the story stays playable.
    public sealed class IslandLayout : MonoBehaviour
    {
        public GameObject IslandPrefab;

        public GameObject IslandRoot { get; private set; }
        public bool UsingGraybox { get; private set; }
        readonly Dictionary<string, Transform> anchors = new Dictionary<string, Transform>();

        // name -> (position, yaw) used when an anchor is missing.
        static readonly Dictionary<string, (Vector3 pos, float yaw)> Fallback = new Dictionary<string, (Vector3, float)>
        {
            { "Anchor_PlayerSpawn", (new Vector3(0f, 0f, -1.5f), 180f) },
            { "Anchor_Lamp_WanFeng", (new Vector3(-5.2f, 0f, -3.2f), 0f) },
            { "Anchor_Lamp_YueChuang", (new Vector3(2.6f, 0f, 1.6f), 0f) },
            { "Anchor_Lamp_GuiHang", (new Vector3(3.4f, 0f, -6.4f), 0f) },
            { "Target_Path", (new Vector3(-7.4f, 0f, -6.2f), 0f) },
            { "Target_Bench", (new Vector3(-4.2f, 0.45f, -6.4f), 0f) },
            { "Target_Window", (new Vector3(3.6f, 1.7f, 2.7f), 0f) },
            { "Target_Pier", (new Vector3(2f, 0.4f, -10f), 0f) },
            { "Target_Sea", (new Vector3(10f, 0f, -40f), 0f) },
            { "Anchor_FlagpoleHook", (new Vector3(2f, 2.4f, -17.75f), 0f) },
            { "NPC_AYing", (new Vector3(2f, 0.4f, -13f), 0f) },
            { "NPC_Postman", (new Vector3(-7.6f, 0f, -4.4f), 60f) },
            // seat anchors: floor level under the seat centre, facing the way the sitter looks
            { "NPC_Bench", (new Vector3(-4.2f, 0f, -6.55f), 0f) },
            { "NPC_ABo_Window", (new Vector3(3.6f, 0f, 3.5f), 180f) },
            { "NPC_ABo_Door", (new Vector3(5.7f, 0f, 2.2f), 200f) },
            { "NPC_DengBo_Box", (new Vector3(2.9f, 0.4f, -17.1f), 270f) },
            { "Cam_Title", (new Vector3(-18f, 16f, -34f), 25f) },
            { "Cam_Puzzle", (new Vector3(-1f, 9.5f, -15.5f), 0f) },
            { "Cam_Pier", (new Vector3(7.5f, 3.2f, -8f), 215f) },
            { "Anchor_VillageGate", (new Vector3(-14f, 2.2f, -2f), 0f) },
            { "Anchor_Boat", (new Vector3(3.6f, 0f, -19f), 180f) },
            { "Anchor_GoldenTree", (new Vector3(6.5f, 0f, -0.5f), 0f) },
            { "Village_Windows", (new Vector3(-26f, 6f, 14f), 0f) },
            { "Sky_ScatterZone_Village", (new Vector3(-26f, 6f, 14f), 0f) },
            { "Sky_ScatterZone_Pier", (new Vector3(2f, 0.4f, -12f), 0f) },
        };

        public void Build()
        {
            if (IslandPrefab != null)
            {
                IslandRoot = Instantiate(IslandPrefab);
                IslandRoot.name = "Island";
            }
            else
            {
                IslandRoot = GrayboxIsland.Build();
                UsingGraybox = true;
            }
            foreach (var t in IslandRoot.GetComponentsInChildren<Transform>(true))
                if (!anchors.ContainsKey(t.name)) anchors[t.name] = t;
            foreach (var kv in Fallback)
            {
                if (anchors.ContainsKey(kv.Key)) continue;
                var go = new GameObject(kv.Key);
                go.transform.SetParent(IslandRoot.transform, false);
                go.transform.SetPositionAndRotation(kv.Value.pos, Quaternion.Euler(0f, kv.Value.yaw, 0f));
                anchors[kv.Key] = go.transform;
                // a real island must carry every anchor; a silent graybox position would misplace the story
                if (!UsingGraybox) Debug.LogError("[JieGuang] Island.prefab lacks required anchor " + kv.Key + "; falling back to a graybox position.");
            }
            if (UsingGraybox) GrayboxIsland.OrientCameras(this);
            else AdoptAtmosphere();
        }

        // The story owns the night: one sky (NightSky) and one directional earthlight. The
        // environment's own sky dome and warm directional lights are switched off; its sea stays.
        void AdoptAtmosphere()
        {
            var atmos = FindChild(IslandRoot.transform, "Atmosphere");
            if (atmos == null) return;
            var envSky = FindChild(atmos, "NightSky");
            if (envSky != null && envSky.TryGetComponent<Renderer>(out var r)) r.enabled = false;
            foreach (var l in atmos.GetComponentsInChildren<Light>(true))
                if (l.type == LightType.Directional) l.enabled = false;
        }

        public Transform Get(string name)
        {
            anchors.TryGetValue(name, out var t);
            return t;
        }

        public Vector3 Pos(string name) => Get(name).position;

        public Transform TargetFor(Target t)
        {
            switch (t)
            {
                case Target.Path: return Get("Target_Path");
                case Target.Bench: return Get("Target_Bench");
                case Target.Window: return Get("Target_Window");
                case Target.Pier: return Get("Target_Pier");
            }
            return null;
        }

        // Where each lamp's head points for directions 0,1 (2 is always straight up). A wide
        // shield that covers two targets (晚风灯 path+bench, 月窗灯 window+pier) aims at the
        // bisector of the two directions so both targets sit inside the cone.
        public Vector3 AimPoint(int lamp, int dir, bool wide)
        {
            dir = LampRules.Wrap(dir);
            Vector3 head = LampHeadPosition(lamp);
            if (dir == 2) return head + new Vector3(0.6f, 12f, 0.4f);
            if (wide && TwinTargets(lamp, dir, out var a, out var b))
            {
                Vector3 da = (a - head).normalized, db = (b - head).normalized;
                float dist = 0.5f * (Vector3.Distance(head, a) + Vector3.Distance(head, b));
                return head + (da + db).normalized * dist;
            }
            switch (lamp)
            {
                case 0: return Pos(dir == 0 ? "Target_Path" : "Target_Bench");
                case 1: return Pos(dir == 0 ? "Target_Window" : "Target_Pier");
                default: return dir == 0 ? Pos("Target_Bench") : Pos("Target_Sea");
            }
        }

        bool TwinTargets(int lamp, int dir, out Vector3 a, out Vector3 b)
        {
            a = b = Vector3.zero;
            if (lamp == 0 && dir == 0) { a = Pos("Target_Path"); b = Pos("Target_Bench"); return true; }
            if (lamp == 1 && dir == 1) { a = Pos("Target_Window"); b = Pos("Target_Pier"); return true; }
            return false;
        }

        // Full cone angle of a lamp's wide shield: the twin targets' separation plus 16 degrees,
        // which leaves 8 degrees of margin on each side.
        public float WideConeAngle(int lamp)
        {
            int dir = lamp == 0 ? 0 : 1;
            if (!TwinTargets(lamp, dir, out var a, out var b)) return 56f;
            Vector3 head = LampHeadPosition(lamp);
            return Mathf.Clamp(Vector3.Angle(a - head, b - head) + 16f, 40f, 80f);
        }

        public Transform LampAnchor(int lamp) =>
            Get(lamp == 0 ? "Anchor_Lamp_WanFeng" : lamp == 1 ? "Anchor_Lamp_YueChuang" : "Anchor_Lamp_GuiHang");

        public Vector3 LampHeadPosition(int lamp)
        {
            var a = LampAnchor(lamp);
            var head = FindChild(a, "LampHead");
            return head != null ? head.position : a.position + Vector3.up * 3.1f;
        }

        public IEnumerable<Transform> VillageWindows()
        {
            var root = Get("Village_Windows");
            if (root == null) yield break;
            foreach (Transform c in root) yield return c;
        }

        public static Transform FindChild(Transform root, string name)
        {
            if (root == null) return null;
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
                if (t.name == name) return t;
            return null;
        }
    }
}
