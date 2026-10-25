using System.Collections;
using UnityEngine;

namespace JieGuang
{
    // Thin wrapper over a character's Animator: locomotion speed plus named action states
    // (state names match the Mixamo clip names, see JieGuangAssetSetup.ActionClips).
    [RequireComponent(typeof(Animator))]
    public sealed class CharacterActor : MonoBehaviour
    {
        public float WalkSpeed = 1.2f;
        public float RunSpeed = 3.2f;
        [Tooltip("Optional bone the lantern hangs from; found automatically when empty.")]
        public Transform LeftHand;
        public Transform RightHand;
        public Transform Head;

        static readonly int SpeedId = Animator.StringToHash("Speed");
        Animator animator;
        float speed, speedTarget;

        public Animator Animator => animator;
        public string CurrentAction { get; private set; } = "Locomotion";

        void Awake()
        {
            animator = GetComponent<Animator>();
            if (animator.isHuman)
            {
                if (LeftHand == null) LeftHand = animator.GetBoneTransform(HumanBodyBones.LeftHand);
                if (RightHand == null) RightHand = animator.GetBoneTransform(HumanBodyBones.RightHand);
                if (Head == null) Head = animator.GetBoneTransform(HumanBodyBones.Head);
            }
        }

        // Planar speed in m/s; the blend tree thresholds are in the same unit.
        public void SetMoveSpeed(float metresPerSecond) => speedTarget = Mathf.Max(0f, metresPerSecond);

        public void Play(string state, float fade = 0.25f)
        {
            CurrentAction = state;
            animator.CrossFadeInFixedTime(state, fade);
        }

        public void ReturnToLocomotion(float fade = 0.3f) => Play("Locomotion", fade);

        // Plays a one-shot clip and waits for it to finish (the controller chains it onward).
        public IEnumerator PlayAndWait(string state, float fade = 0.2f)
        {
            Play(state, fade);
            yield return null;
            yield return new WaitForSeconds(fade);
            var info = animator.GetCurrentAnimatorStateInfo(0);
            yield return new WaitForSeconds(Mathf.Max(0f, info.length * 0.92f - fade));
        }

        public void FaceTowards(Vector3 worldPoint, float maxDegrees = 360f)
        {
            Vector3 d = worldPoint - transform.position;
            d.y = 0f;
            if (d.sqrMagnitude < 1e-4f) return;
            transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(d), maxDegrees);
        }

        void Update()
        {
            speed = Mathf.MoveTowards(speed, speedTarget, Time.deltaTime * 6f);
            animator.SetFloat(SpeedId, speed);
        }
    }
}
