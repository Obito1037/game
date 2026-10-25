using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace JieGuang.EditorTools
{
    // Verification scene: the five rigged characters side by side, each driven by
    // LineupPose so retargeted Mixamo clips can be captured in Play Mode.
    public static class CharacterLineupTest
    {
        public const string ScenePath = "Assets/JieGuang/Scenes/Tests/CharacterLineup.unity";

        [MenuItem("JieGuang/Tests/Build Character Lineup Scene")]
        public static void Build()
        {
            System.IO.Directory.CreateDirectory("Assets/JieGuang/Scenes/Tests");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var cam = new GameObject("Camera").AddComponent<Camera>();
            cam.tag = "MainCamera";
            cam.transform.position = new Vector3(0f, 1.2f, 7.5f);
            cam.transform.rotation = Quaternion.Euler(4f, 180f, 0f);
            cam.fieldOfView = 38f;
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.55f, 0.57f, 0.6f);
            var sun = new GameObject("Key").AddComponent<Light>();
            sun.type = LightType.Directional;
            sun.intensity = 1.6f;
            sun.transform.rotation = Quaternion.Euler(35f, 150f, 0f);
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Flat;
            RenderSettings.ambientLight = new Color(0.55f, 0.55f, 0.6f);
            var floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
            floor.transform.localScale = new Vector3(3f, 1f, 2f);
            string[] ids = { "xiaodenglong", "aying", "postman", "abo", "dengbo" };
            for (int i = 0; i < ids.Length; ++i)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/JieGuang/Prefabs/Characters/" + ids[i] + ".prefab");
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab);
                go.transform.position = new Vector3((i - 2) * 1.3f, 0f, 0f);
                go.AddComponent<LineupPose>();
            }
            EditorSceneManager.SaveScene(scene, ScenePath);
        }
    }
}
