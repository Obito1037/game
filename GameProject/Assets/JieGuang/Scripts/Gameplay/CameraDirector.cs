using UnityEngine;
using UnityEngine.InputSystem;
using UnityEngine.Rendering.Universal;

namespace JieGuang
{
    // One camera with two modes: an orbit follow camera for walking (right mouse / gamepad
    // right stick to look, wheel to zoom) and fixed story shots that it glides to.
    public sealed class CameraDirector : MonoBehaviour
    {
        public Transform Follow;
        public float Distance = 4.2f;
        public float MinDistance = 2f, MaxDistance = 9f;
        public float Yaw, Pitch = 16f;

        Camera cam;
        bool shotMode;
        Vector3 shotPos;
        Quaternion shotRot;
        float shotSpeed = 1.5f;

        public Camera Camera => cam;
        public bool InShot => shotMode;

        public static CameraDirector Create()
        {
            var go = new GameObject("Main Camera");
            go.tag = "MainCamera";
            var c = go.AddComponent<Camera>();
            c.nearClipPlane = 0.08f;
            c.farClipPlane = 600f;
            c.fieldOfView = 50f;
            c.clearFlags = CameraClearFlags.SolidColor;
            c.allowHDR = true;
            // URP leaves post-processing off per camera by default; Volumes only apply once it is on
            var data = c.GetUniversalAdditionalCameraData();
            data.renderPostProcessing = true;
            data.volumeLayerMask = LayerMask.GetMask("Default");
            // PC uses native-resolution FXAA with the v2 pipeline's MSAA disabled.
            // Mobile/Web remains on its existing quality profile and camera AA behavior.
            data.antialiasing = QualitySettings.GetQualityLevel() == 1
                ? AntialiasingMode.FastApproximateAntialiasing : AntialiasingMode.None;
            go.AddComponent<AudioListener>();
            var d = go.AddComponent<CameraDirector>();
            d.cam = c;
            return d;
        }

        public void Shot(Transform anchor, float speed = 1.5f) => Shot(anchor.position, anchor.rotation, speed);

        public void Shot(Vector3 pos, Quaternion rot, float speed = 1.5f)
        {
            shotMode = true;
            shotPos = pos;
            shotRot = rot;
            shotSpeed = speed;
        }

        public void ShotLookAt(Vector3 pos, Vector3 target, float speed = 1.5f) =>
            Shot(pos, Quaternion.LookRotation(target - pos, Vector3.up), speed);

        public void Cut(Vector3 pos, Quaternion rot)
        {
            Shot(pos, rot);
            transform.SetPositionAndRotation(pos, rot);
        }

        public void FollowPlayer(bool snapBehind = false)
        {
            shotMode = false;
            if (snapBehind && Follow != null) Yaw = Follow.eulerAngles.y;
        }

        void LateUpdate()
        {
            float dt = Time.deltaTime;
            if (shotMode)
            {
                float k = 1f - Mathf.Exp(-shotSpeed * dt * 2f);
                transform.position = Vector3.Lerp(transform.position, shotPos, k);
                transform.rotation = Quaternion.Slerp(transform.rotation, shotRot, k);
                return;
            }
            if (Follow == null) return;
            var mouse = Mouse.current;
            if (mouse != null)
            {
                if (mouse.rightButton.isPressed)
                {
                    Vector2 d = mouse.delta.ReadValue();
                    Yaw += d.x * 0.18f;
                    Pitch = Mathf.Clamp(Pitch - d.y * 0.12f, -10f, 70f);
                }
                float scroll = mouse.scroll.ReadValue().y;
                if (Mathf.Abs(scroll) > 0.01f) Distance = Mathf.Clamp(Distance - Mathf.Sign(scroll) * 0.4f, MinDistance, MaxDistance);
            }
            var pad = Gamepad.current;
            if (pad != null)
            {
                Vector2 r = pad.rightStick.ReadValue();
                Yaw += r.x * 120f * dt;
                Pitch = Mathf.Clamp(Pitch - r.y * 80f * dt, -10f, 70f);
            }
            Vector3 pivot = Follow.position + Vector3.up * 1.25f;
            Quaternion rot = Quaternion.Euler(Pitch, Yaw, 0f);
            Vector3 want = pivot - rot * Vector3.forward * Distance;
            // keep the camera out of walls and terrain
            if (Physics.SphereCast(pivot, 0.2f, (want - pivot).normalized, out var hit, Distance, ~(1 << 2), QueryTriggerInteraction.Ignore))
                want = pivot + (want - pivot).normalized * Mathf.Max(0.6f, hit.distance - 0.1f);
            float k2 = 1f - Mathf.Exp(-8f * dt);
            transform.position = Vector3.Lerp(transform.position, want, k2);
            transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(pivot - transform.position, Vector3.up), k2);
        }
    }
}
