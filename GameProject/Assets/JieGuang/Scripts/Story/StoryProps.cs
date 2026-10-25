using UnityEngine;

namespace JieGuang
{
    // Runtime placement of the three small story props. Prefab conversion rotations are retained.
    public sealed class StoryProps : MonoBehaviour
    {
        Lantern lantern;
        CharacterActor postman, reader;
        GameObject fruit, letter, cane;
        Renderer[] fruitRenderers;
        bool caneVisible;

        public void Setup(Lantern carriedLantern, CharacterActor mailman, CharacterActor player)
        {
            lantern = carriedLantern;
            postman = mailman;
            reader = player;
            fruit = Model("B02_light_fruit", lantern.transform);
            if (fruit != null)
            {
                fruit.transform.localPosition = new Vector3(0f, -.21f, 0f);
                fruitRenderers = fruit.GetComponentsInChildren<Renderer>();
                foreach (var r in fruitRenderers) r.material.EnableKeyword("_EMISSION");
            }
            letter = Model("B03_firefly_letter", transform);
            if (letter != null) letter.SetActive(false);
            var caneRoot = new GameObject("PostmanCane");
            caneRoot.transform.SetParent(transform, false);
            cane = caneRoot;
            var model = Model("B04_cane", caneRoot.transform);
            if (model != null)
            {
                // The source cane itself leans diagonally. Its mesh principal axis, measured
                // in Blender, becomes (-.054, .740, .671) in Unity after axis conversion.
                model.transform.localRotation = Quaternion.FromToRotation(new Vector3(-.054f, .740f, .671f), Vector3.up) * model.transform.localRotation;
                var renderers = model.GetComponentsInChildren<Renderer>();
                if (renderers.Length > 0)
                {
                    var b = renderers[0].bounds;
                    foreach (var r in renderers) b.Encapsulate(r.bounds);
                    float scale = .96f / Mathf.Max(.01f, b.size.y);
                    model.transform.localScale *= scale;
                    b = renderers[0].bounds;
                    foreach (var r in renderers) b.Encapsulate(r.bounds);
                    model.transform.position -= new Vector3(b.center.x, b.min.y, b.center.z);
                }
            }
            cane.SetActive(false);
        }

        static GameObject Model(string name, Transform parent)
        {
            var prefab = Resources.Load<GameObject>("Props/" + name);
            if (prefab == null) return null;
            var go = Instantiate(prefab, parent, false);
            go.name = name;
            go.transform.localPosition = Vector3.zero;
            go.transform.localRotation = prefab.transform.localRotation;
            foreach (var c in go.GetComponentsInChildren<Collider>()) Destroy(c);
            return go;
        }

        public void SetChapter(Chapter chapter)
        {
            ShowLetter(false);
            caneVisible = chapter == Chapter.One || chapter == Chapter.Epilogue;
        }

        public void ShowLetter(bool visible)
        {
            if (letter == null) return;
            letter.SetActive(visible);
            if (!visible) return;
            // The fold sits in his right hand; keep the prefab's axis conversion, never float it.
            letter.transform.position = reader.RightHand != null ? reader.RightHand.position : reader.transform.position + reader.transform.forward * .34f + Vector3.up * .87f;
            var prefab = Resources.Load<GameObject>("Props/B03_firefly_letter");
            letter.transform.rotation = reader.transform.rotation * prefab.transform.localRotation;
        }

        void LateUpdate()
        {
            if (letter != null && letter.activeSelf && reader.RightHand != null)
                letter.transform.position = reader.RightHand.position;
            if (fruitRenderers != null)
                foreach (var r in fruitRenderers)
                    MaterialKit.SetEmission(r, new Color(1f, .64f, .25f) * Mathf.Max(0, lantern.Brightness) * 1.2f);
            if (cane == null) return;
            bool show = caneVisible && postman != null && postman.gameObject.activeInHierarchy;
            cane.SetActive(show);
            if (!show) return;
            Vector3 pos = postman.transform.position + postman.transform.right * .43f + postman.transform.forward * (postman.CurrentAction.StartsWith("Sit_") ? .58f : .12f);
            // Ground the cane alongside the postman; never inherit an animated hand's pitch.
            cane.transform.SetPositionAndRotation(pos, postman.transform.rotation);
        }
    }
}
