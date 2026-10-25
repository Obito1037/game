using UnityEngine;
using UnityEngine.InputSystem;

namespace JieGuang
{
    // Third-person walking for 小灯笼: camera-relative WASD, Shift to run, gravity and steps
    // through a CharacterController. Input is ignored while the director has control.
    [RequireComponent(typeof(CharacterController))]
    public sealed class PlayerController : MonoBehaviour
    {
        public float WalkSpeed = 1.6f;
        public float RunSpeed = 3.2f;
        public bool InputEnabled = true;
        public Transform CameraTransform;

        CharacterController cc;
        CharacterActor actor;
        float vy;

        void Awake()
        {
            cc = GetComponent<CharacterController>();
            actor = GetComponent<CharacterActor>();
        }

        public static PlayerController Attach(GameObject character, float height)
        {
            var cc = character.AddComponent<CharacterController>();
            cc.height = height * 0.95f;
            cc.radius = 0.24f;
            cc.center = new Vector3(0f, cc.height / 2f + 0.02f, 0f);
            cc.stepOffset = 0.35f;
            cc.slopeLimit = 48f;
            cc.skinWidth = 0.03f;
            return character.AddComponent<PlayerController>();
        }

        public void Teleport(Vector3 pos, float yaw)
        {
            cc.enabled = false;
            transform.SetPositionAndRotation(pos, Quaternion.Euler(0f, yaw, 0f));
            cc.enabled = true;
            vy = 0f;
        }

        // Used by scripted walks: move toward a point at the given speed this frame.
        public bool StepTowards(Vector3 target, float speed, float stopDistance = 0.15f)
        {
            Vector3 d = target - transform.position;
            d.y = 0f;
            if (d.magnitude <= stopDistance) { actor.SetMoveSpeed(0f); return true; }
            Vector3 dir = d.normalized;
            transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(dir), 540f * Time.deltaTime);
            Move(dir * speed);
            actor.SetMoveSpeed(speed);
            return false;
        }

        void Move(Vector3 planar)
        {
            vy = cc.isGrounded ? -1f : vy - 9.81f * Time.deltaTime;
            cc.Move((planar + Vector3.up * vy) * Time.deltaTime);
        }

        void Update()
        {
            if (!InputEnabled) { if (cc.enabled) Move(Vector3.zero); return; }
            Vector2 input = Vector2.zero;
            if (GameInput.Held(Key.W) || GameInput.Held(Key.UpArrow)) input.y += 1f;
            if (GameInput.Held(Key.S) || GameInput.Held(Key.DownArrow)) input.y -= 1f;
            if (GameInput.Held(Key.D) || GameInput.Held(Key.RightArrow)) input.x += 1f;
            if (GameInput.Held(Key.A) || GameInput.Held(Key.LeftArrow)) input.x -= 1f;
            var pad = Gamepad.current;
            if (pad != null && pad.leftStick.ReadValue().sqrMagnitude > 0.04f) input = pad.leftStick.ReadValue();
            input = Vector2.ClampMagnitude(input, 1f);
            bool run = GameInput.Held(Key.LeftShift);
            Vector3 fwd = CameraTransform != null ? CameraTransform.forward : Vector3.forward;
            fwd.y = 0f;
            fwd.Normalize();
            Vector3 right = new Vector3(fwd.z, 0f, -fwd.x);
            Vector3 dir = fwd * input.y + right * input.x;
            float speed = (run ? RunSpeed : WalkSpeed) * dir.magnitude;
            if (dir.sqrMagnitude > 1e-3f)
                transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(dir), 600f * Time.deltaTime);
            Move(dir.normalized * speed);
            actor.SetMoveSpeed(speed);
        }
    }
}
