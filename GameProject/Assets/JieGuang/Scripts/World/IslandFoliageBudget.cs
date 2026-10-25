using UnityEngine;

namespace JieGuang
{
    // Explicit geometry makes foliage work with normal cameras and offline camera captures.
    // Small mesh chunks provide frustum culling, plus cheaper far meshes and platform budgets.
    public sealed class IslandFoliageBudget : MonoBehaviour
    {
        public MeshFilter[] Chunks;
        public Mesh[] FullMeshes;
        public Mesh[] ReducedMeshes;
        public float DesktopDistance = 48f;
        public float BrowserDistance = 32f;
        public float DesktopFullDistance = 18f;
        public float BrowserFullDistance = 12f;

        Renderer[] renderers;
        Camera view;
        float nextUpdate;
        float distance;
        float fullDistance;
        static readonly int FadeId = Shader.PropertyToID("_FoliageDistance");

        void OnEnable()
        {
            if (Chunks == null) return;
            bool browser = Application.platform == RuntimePlatform.WebGLPlayer;
            distance = browser ? BrowserDistance : DesktopDistance;
            fullDistance = browser ? BrowserFullDistance : DesktopFullDistance;
            renderers = new Renderer[Chunks.Length];
            var block = new MaterialPropertyBlock();
            block.SetFloat(FadeId, distance);
            for (int i = 0; i < Chunks.Length; i++)
            {
                if (Chunks[i] == null) continue;
                renderers[i] = Chunks[i].GetComponent<Renderer>();
                renderers[i].SetPropertyBlock(block);
            }
            nextUpdate = 0f;
        }

        void LateUpdate()
        {
            if (renderers == null || Time.unscaledTime < nextUpdate) return;
            nextUpdate = Time.unscaledTime + .25f;
            if (view == null || !view.isActiveAndEnabled) view = Camera.main;
            if (view == null) return;
            var position = view.transform.position;
            for (int i = 0; i < renderers.Length; i++)
            {
                var r = renderers[i];
                if (r == null) continue;
                float d = Vector3.Distance(position, r.bounds.ClosestPoint(position));
                r.enabled = d < distance + 2f;
                if (r.enabled && FullMeshes != null && ReducedMeshes != null && i < FullMeshes.Length && i < ReducedMeshes.Length)
                {
                    var desired = d < fullDistance ? FullMeshes[i] : ReducedMeshes[i];
                    if (Chunks[i].sharedMesh != desired) Chunks[i].sharedMesh = desired;
                }
            }
        }

        void OnDisable()
        {
            // Restoring visibility also keeps an intentionally disabled budget component useful
            // for camera-only diagnostics and avoids leaving distant chunks permanently hidden.
            if (renderers == null) return;
            foreach (var r in renderers) if (r != null) r.enabled = true;
        }
    }
}
