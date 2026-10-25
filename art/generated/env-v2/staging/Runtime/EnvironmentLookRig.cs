using UnityEngine;
using UnityEngine.Rendering;

namespace JieGuang.EnvironmentTools
{
    /// <summary>Explicit chapter interface, owned by Environment. No Awake/Update/OnEnable scene mutation.</summary>
    public sealed class EnvironmentLookRig : MonoBehaviour
    {
        public EnvironmentLookLibrary library;
        public Volume volume;
        public Light warmKey, warmFill;
        public Renderer skyRenderer, seaRenderer;
        public string currentLook = "night-1";
        MaterialPropertyBlock skyBlock, seaBlock;

        // Caller may choose applyGlobalEnvironment only when it owns ambient/fog updates.
        public void ApplyChapter(string id, bool applyGlobalEnvironment = false)
        {
            if (library == null) throw new System.InvalidOperationException("Environment look library is missing.");
            var look = library.Get(id);
            currentLook = id;
            if (volume != null) volume.sharedProfile = look.profile;
            if (warmKey != null) { warmKey.color = look.keyColor; warmKey.intensity = look.keyIntensity; }
            if (warmFill != null) { warmFill.color = look.fillColor; warmFill.intensity = look.fillIntensity; }
            if (skyRenderer != null)
            {
                if (skyBlock == null) skyBlock = new MaterialPropertyBlock();
                skyRenderer.GetPropertyBlock(skyBlock);
                skyBlock.SetColor("_Zenith", look.zenith);
                skyBlock.SetColor("_Horizon", look.horizon);
                skyBlock.SetFloat("_EarthLitFraction", look.earthLitFraction);
                skyBlock.SetFloat("_Stars", look.stars);
                skyBlock.SetFloat("_CloudOpacity", look.cloudOpacity);
                skyRenderer.SetPropertyBlock(skyBlock);
            }
            if (seaRenderer != null)
            {
                if (seaBlock == null) seaBlock = new MaterialPropertyBlock();
                seaRenderer.GetPropertyBlock(seaBlock);
                seaBlock.SetColor("_Deep", look.seaDeep);
                seaBlock.SetColor("_Shallow", look.seaShallow);
                seaBlock.SetColor("_Horizon", look.horizon);
                seaRenderer.SetPropertyBlock(seaBlock);
            }
            if (applyGlobalEnvironment) EnvironmentLookLibrary.ApplyGlobalEnvironment(look);
        }
    }
}
