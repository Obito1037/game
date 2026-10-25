using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace JieGuang.EditorTools
{
    // Import rules for the rigged characters (art/generated/characters-v1) and the Mixamo clips.
    public sealed class JieGuangModelImport : AssetPostprocessor
    {
        const string CharacterRoot = "Assets/JieGuang/Characters/";
        const string MixamoRoot = "Assets/JieGuang/Animations/Mixamo/";

        static readonly HashSet<string> Looping = new HashSet<string>
        {
            "Idle_Breathing", "Idle_OldMan", "Idle_Sad", "Idle_Happy", "Walk_Male", "Walk_Female",
            "Walk_OldMan", "Walk_Sad", "Run_Happy", "Sit_Idle", "Sit_Writing", "Sit_Talking",
            "Kneel_Idle", "Talk", "Look_Around"
        };

        void OnPreprocessModel()
        {
            if (!assetPath.StartsWith(CharacterRoot) && !assetPath.StartsWith(MixamoRoot)) return;
            var importer = (ModelImporter)assetImporter;
            importer.animationType = ModelImporterAnimationType.Human;
            importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            importer.materialImportMode = ModelImporterMaterialImportMode.None;
            importer.importCameras = false;
            importer.importLights = false;
            importer.importBlendShapes = false;
            importer.importAnimation = assetPath.StartsWith(MixamoRoot);
            if (assetPath.StartsWith(CharacterRoot))
            {
                importer.optimizeGameObjects = false;
                importer.meshCompression = ModelImporterMeshCompression.Off;
            }
        }

        void OnPreprocessAnimation()
        {
            if (!assetPath.StartsWith(MixamoRoot)) return;
            var importer = (ModelImporter)assetImporter;
            string name = Path.GetFileNameWithoutExtension(assetPath);
            ModelImporterClipAnimation[] clips = importer.clipAnimations.Length > 0
                ? importer.clipAnimations : importer.defaultClipAnimations;
            foreach (var c in clips)
            {
                c.name = name;
                c.loopTime = Looping.Contains(name);
                c.loopPose = c.loopTime;
                // In-place playback: the GameObject is moved by game code, never by root motion.
                c.lockRootRotation = true;
                c.keepOriginalOrientation = true;
                c.lockRootHeightY = true;
                c.keepOriginalPositionY = true;
                c.lockRootPositionXZ = true;
                c.keepOriginalPositionXZ = true;
            }
            importer.clipAnimations = clips;
        }
    }

    public static class JieGuangAssetSetup
    {
        public sealed class CharacterSpec
        {
            public string Id, Idle, Walk, Run;
            public float WalkSpeed, RunSpeed;
        }

        public static readonly CharacterSpec[] Characters =
        {
            new CharacterSpec { Id = "xiaodenglong", Idle = "Idle_Breathing", Walk = "Walk_Male", Run = "Run_Happy", WalkSpeed = 1.2f, RunSpeed = 3.2f },
            new CharacterSpec { Id = "aying", Idle = "Idle_Happy", Walk = "Walk_Female", Run = "Run_Happy", WalkSpeed = 1.2f, RunSpeed = 3.4f },
            new CharacterSpec { Id = "postman", Idle = "Idle_OldMan", Walk = "Walk_OldMan", Run = "Walk_OldMan", WalkSpeed = 0.6f, RunSpeed = 0.9f },
            new CharacterSpec { Id = "abo", Idle = "Idle_Breathing", Walk = "Walk_Female", Run = "Walk_Female", WalkSpeed = 0.8f, RunSpeed = 1.0f },
            new CharacterSpec { Id = "dengbo", Idle = "Idle_OldMan", Walk = "Walk_OldMan", Run = "Walk_OldMan", WalkSpeed = 0.7f, RunSpeed = 1.0f },
        };

        // One-shot / looping action states every controller gets; game code CrossFades by name.
        public static readonly string[] ActionClips =
        {
            "Idle_Sad", "Idle_Happy", "Walk_Sad", "Sit_Down", "Sit_Idle", "Sit_StandUp", "Sit_Writing", "Sit_Talking",
            "Kneel_Down", "Kneel_Idle", "Kneel_StandUp", "Wave", "Talk", "Point_Forward", "Reach_Out",
            "Look_Around", "Turn_Left", "Turn_Right", "PickUp_OneHand"
        };

        const string Root = "Assets/JieGuang";

        [MenuItem("JieGuang/Build Character Prefabs")]
        public static void BuildAll()
        {
            Directory.CreateDirectory(Root + "/Prefabs/Characters");
            Directory.CreateDirectory(Root + "/Animations/Controllers");
            Directory.CreateDirectory(Root + "/Materials/Characters");
            foreach (var spec in Characters) Build(spec);
            AssetDatabase.SaveAssets();
            Debug.Log("[JieGuang] character prefabs built: " + Characters.Length);
        }

        static AnimationClip Clip(string name)
        {
            string path = Root + "/Animations/Mixamo/" + name + ".fbx";
            var clip = AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>()
                .FirstOrDefault(c => !c.name.StartsWith("__preview__"));
            if (clip == null) throw new FileNotFoundException("Missing Mixamo clip " + path);
            return clip;
        }

        static AnimatorController BuildController(CharacterSpec spec)
        {
            string path = Root + "/Animations/Controllers/" + spec.Id + ".controller";
            AssetDatabase.DeleteAsset(path);
            var ctrl = AnimatorController.CreateAnimatorControllerAtPath(path);
            ctrl.AddParameter("Speed", AnimatorControllerParameterType.Float);
            var sm = ctrl.layers[0].stateMachine;

            var tree = new BlendTree { name = "Locomotion", blendParameter = "Speed", useAutomaticThresholds = false, hideFlags = HideFlags.HideInHierarchy };
            AssetDatabase.AddObjectToAsset(tree, ctrl);
            tree.AddChild(Clip(spec.Idle), 0f);
            tree.AddChild(Clip(spec.Walk), spec.WalkSpeed);
            tree.AddChild(Clip(spec.Run), spec.RunSpeed);
            var loco = sm.AddState("Locomotion");
            loco.motion = tree;
            sm.defaultState = loco;

            foreach (string a in ActionClips)
            {
                var st = sm.AddState(a);
                st.motion = Clip(a);
            }
            // One-shot clips return to their natural follow-up state.
            Chain(sm, "Sit_Down", "Sit_Idle");
            Chain(sm, "Sit_StandUp", "Locomotion");
            Chain(sm, "Kneel_Down", "Kneel_Idle");
            Chain(sm, "Kneel_StandUp", "Locomotion");
            foreach (string a in new[] { "Wave", "Point_Forward", "Reach_Out", "Turn_Left", "Turn_Right", "PickUp_OneHand" })
                Chain(sm, a, "Locomotion");
            return ctrl;
        }

        static void Chain(AnimatorStateMachine sm, string from, string to)
        {
            var a = sm.states.First(s => s.state.name == from).state;
            var b = sm.states.First(s => s.state.name == to).state;
            var t = a.AddTransition(b);
            t.hasExitTime = true;
            t.exitTime = 0.92f;
            t.duration = 0.2f;
        }

        static void Build(CharacterSpec spec)
        {
            string dir = Root + "/Characters/" + spec.Id;
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(dir + "/" + spec.Id + ".fbx");
            var tex = AssetDatabase.LoadAssetAtPath<Texture2D>(dir + "/" + spec.Id + "_albedo.jpg");
            if (model == null || tex == null) throw new FileNotFoundException("Missing character assets in " + dir);

            string matPath = Root + "/Materials/Characters/" + spec.Id + ".mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(matPath);
            if (mat == null)
            {
                mat = new Material(Shader.Find("Universal Render Pipeline/Lit"));
                AssetDatabase.CreateAsset(mat, matPath);
            }
            mat.SetTexture("_BaseMap", tex);
            mat.SetColor("_BaseColor", Color.white);
            mat.SetFloat("_Smoothness", 0.18f);
            mat.SetFloat("_Metallic", 0f);
            EditorUtility.SetDirty(mat);

            var ctrl = BuildController(spec);
            var go = (GameObject)PrefabUtility.InstantiatePrefab(model);
            go.name = spec.Id;
            foreach (var r in go.GetComponentsInChildren<SkinnedMeshRenderer>())
            {
                r.sharedMaterial = mat;
                r.updateWhenOffscreen = true;
            }
            var anim = go.GetComponent<Animator>() ?? go.AddComponent<Animator>();
            anim.runtimeAnimatorController = ctrl;
            anim.applyRootMotion = false;
            anim.cullingMode = AnimatorCullingMode.CullUpdateTransforms;
            var actor = go.GetComponent<JieGuang.CharacterActor>() ?? go.AddComponent<JieGuang.CharacterActor>();
            actor.WalkSpeed = spec.WalkSpeed;
            actor.RunSpeed = spec.RunSpeed;
            PrefabUtility.SaveAsPrefabAsset(go, Root + "/Prefabs/Characters/" + spec.Id + ".prefab");
            Object.DestroyImmediate(go);
        }
    }
}
