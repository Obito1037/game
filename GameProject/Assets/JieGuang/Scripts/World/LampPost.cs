using UnityEngine;

namespace JieGuang
{
    // One of the cape's three street lamps: turns its head toward the chosen aim point,
    // switches between a wide and a narrow shield, and draws a soft visible beam.
    public sealed class LampPost : MonoBehaviour
    {
        public const float NarrowAngle = 25f;
        // full cone angle of the wide shield; the director sizes it to the lamp's two targets
        public float WideAngle = 56f;
        public static readonly Color Amber = new Color(1f, 0.74f, 0.42f);

        public int Index;
        public Transform Head { get; private set; }
        public bool Selected { get; set; }

        Light spot;
        Transform beam, marker;
        GameObject shadeWide, shadeNarrow;
        // Orientation of the Tripo shade models relative to the lamp head's beam axis (+Z).
        public static Vector3 ShadeEuler = new Vector3(0f, 0f, 0f);
        public static float ShadeForward = 0.24f;

        // The brass shade on the head is the visible wide/narrow choice.
        GameObject SpawnShade(string resource)
        {
            var prefab = Resources.Load<GameObject>(resource);
            if (prefab == null) return null;
            var go = Instantiate(prefab, Head);
            go.name = resource.Substring(resource.LastIndexOf('/') + 1);
            go.transform.localRotation = Quaternion.Euler(ShadeEuler) * prefab.transform.localRotation;
            go.transform.localPosition = new Vector3(0f, 0f, ShadeForward) / Mathf.Max(Head.lossyScale.x, 1e-3f);
            go.transform.localScale = Vector3.one / Mathf.Max(Head.lossyScale.x, 1e-3f);
            foreach (var c in go.GetComponentsInChildren<Collider>()) Destroy(c);
            go.SetActive(false);
            return go;
        }
        Renderer bulb;
        Material beamMat;
        static readonly int BeamDensity = Shader.PropertyToID("_BeamDensity");
        LampSetting state = new LampSetting();
        Vector3 aim;
        float onLevel, angle = NarrowAngle;

        public void Setup(int index, Transform anchor)
        {
            Index = index;
            name = "Lamp_" + LampRules.LampNames[index];
            transform.SetParent(anchor, false);
            Head = IslandLayout.FindChild(anchor, "LampHead");
            if (Head == null) Head = BuildGraybox();
            // the environment's lamp heads already carry a Spot child (+Z is the beam)
            var existing = IslandLayout.FindChild(Head, "Spot");
            spot = existing != null ? existing.GetComponent<Light>() : null;
            if (spot == null)
            {
                var lightGo = new GameObject("Spot");
                lightGo.transform.SetParent(Head, false);
                spot = lightGo.AddComponent<Light>();
            }
            spot.type = LightType.Spot;
            spot.color = Amber;
            spot.range = 20f;
            spot.intensity = 0f;
            spot.shadows = LightShadows.Hard; // hard local shadows: about half the cost on integrated GPUs
            spot.shadowStrength = 0.75f;
            beam = BuildBeam(Head);
            shadeWide = SpawnShade("Props/A07_shade_wide");
            shadeNarrow = SpawnShade("Props/A07_shade_narrow");
            marker = GameObject.CreatePrimitive(PrimitiveType.Sphere).transform;
            Destroy(marker.GetComponent<Collider>());
            marker.SetParent(transform, false);
            marker.position = Head.position + Vector3.up * 0.75f;
            marker.localScale = Vector3.one * 0.22f;
            marker.GetComponent<Renderer>().sharedMaterial = MaterialKit.Additive(new Color(1f, 0.8f, 0.4f, 0.9f));
        }

        Transform BuildGraybox()
        {
            var dark = MaterialKit.Lit(new Color(0.22f, 0.17f, 0.13f), 0.35f);
            var post = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            post.name = "Post";
            post.transform.SetParent(transform, false);
            post.transform.localPosition = new Vector3(0f, 1.5f, 0f);
            post.transform.localScale = new Vector3(0.14f, 1.5f, 0.14f);
            post.GetComponent<Renderer>().sharedMaterial = dark;
            var head = new GameObject("LampHead").transform;
            head.SetParent(transform, false);
            head.localPosition = new Vector3(0f, 3.15f, 0f);
            var cap = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            Destroy(cap.GetComponent<Collider>());
            cap.transform.SetParent(head, false);
            cap.transform.localScale = new Vector3(0.42f, 0.16f, 0.42f);
            cap.transform.localEulerAngles = new Vector3(90f, 0f, 0f);
            cap.transform.localPosition = new Vector3(0f, 0f, -0.08f);
            cap.GetComponent<Renderer>().sharedMaterial = MaterialKit.Lit(new Color(0.55f, 0.36f, 0.2f), 0.5f);
            var glass = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            Destroy(glass.GetComponent<Collider>());
            glass.transform.SetParent(head, false);
            glass.transform.localScale = Vector3.one * 0.26f;
            glass.transform.localPosition = new Vector3(0f, 0f, 0.08f);
            bulb = glass.GetComponent<Renderer>();
            bulb.material = MaterialKit.LitInstance(new Color(0.9f, 0.8f, 0.6f), Color.black);
            return head;
        }

        static Mesh coneMesh;

        static Mesh Cone()
        {
            if (coneMesh != null) return coneMesh;
            const int seg = 24;
            var v = new Vector3[seg * 2];
            var normals = new Vector3[seg * 2];
            var uv = new Vector2[seg * 2];
            var tris = new int[seg * 6];
            for (int i = 0; i < seg; ++i)
            {
                float a = i * Mathf.PI * 2f / seg;
                v[i] = new Vector3(Mathf.Cos(a) * 0.04f, Mathf.Sin(a) * 0.04f, 0f);
                v[i + seg] = new Vector3(Mathf.Cos(a), Mathf.Sin(a), 1f);
                // Analytic smooth normals survive the beam's nonuniform radius/length scale.
                normals[i] = normals[i + seg] = new Vector3(Mathf.Cos(a), Mathf.Sin(a), -0.96f).normalized;
                uv[i] = new Vector2((float)i / seg, 0f);
                uv[i + seg] = new Vector2((float)i / seg, 1f);
                int n = (i + 1) % seg;
                tris[i * 6] = i; tris[i * 6 + 1] = n; tris[i * 6 + 2] = i + seg;
                tris[i * 6 + 3] = n; tris[i * 6 + 4] = n + seg; tris[i * 6 + 5] = i + seg;
            }
            coneMesh = new Mesh { name = "BeamCone", vertices = v, normals = normals, uv = uv, triangles = tris };
            coneMesh.RecalculateBounds();
            return coneMesh;
        }

        Transform BuildBeam(Transform head)
        {
            var go = new GameObject("Beam");
            go.transform.SetParent(head, false);
            go.AddComponent<MeshFilter>().sharedMesh = Cone();
            var r = go.AddComponent<MeshRenderer>();
            // Explicit Resources material keeps the dedicated shader in native/WebGL builds.
            beamMat = new Material(Resources.Load<Material>("Materials/Base_Beam"));
            MaterialKit.SetColor(beamMat, new Color(1f, 0.7f, 0.38f, 1f));
            beamMat.SetFloat(BeamDensity, 0f);
            r.sharedMaterial = beamMat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            // One double-sided shell: the shader softens its silhouette and opaque contacts.
            return go.transform;
        }

        public void Apply(LampSetting s, Vector3 aimPoint, bool instant = false)
        {
            state = s.Clone();
            aim = aimPoint;
            if (instant)
            {
                onLevel = s.On ? 1f : 0f;
                angle = s.Wide ? WideAngle : NarrowAngle;
                Head.rotation = Quaternion.LookRotation(aim - Head.position);
            }
        }

        void LateUpdate()
        {
            if (Head == null) return;
            float dt = Time.deltaTime;
            onLevel = Mathf.MoveTowards(onLevel, state.On ? 1f : 0f, dt * 1.5f);
            angle = Mathf.MoveTowards(angle, state.Wide ? WideAngle : NarrowAngle, dt * 120f);
            var want = Quaternion.LookRotation(aim - Head.position);
            Head.rotation = Quaternion.RotateTowards(Head.rotation, want, dt * 140f);
            spot.spotAngle = angle;
            spot.innerSpotAngle = angle * 0.55f;
            // a narrow beam concentrates the same light
            // tuned on the real island: 5-9 m throws must read against the 1.0 earthlight
            spot.intensity = onLevel * (state.Wide ? 40f : 60f);
            float len = Mathf.Clamp(Vector3.Distance(Head.position, aim) + 1f, 3f, 14f);
            float rad = Mathf.Tan(angle * 0.5f * Mathf.Deg2Rad) * len;
            beam.localScale = new Vector3(rad, rad, len);
            beam.gameObject.SetActive(onLevel > 0.01f);
            // The old additive material stored density in a Color RGB channel. Match its
            // linear-space energy explicitly; a raw .14 alpha was about eight times brighter.
            beamMat.SetFloat(BeamDensity, Mathf.GammaToLinearSpace(state.Wide ? 0.07f : 0.14f) * onLevel);
            if (bulb != null) MaterialKit.SetEmission(bulb, Amber * (3f * onLevel));
            if (shadeWide != null) shadeWide.SetActive(state.Wide);
            if (shadeNarrow != null) shadeNarrow.SetActive(!state.Wide);
            marker.gameObject.SetActive(Selected);
            if (Selected) marker.position = Head.position + Vector3.up * (0.75f + Mathf.Sin(Time.time * 3f) * 0.08f);
        }
    }
}
