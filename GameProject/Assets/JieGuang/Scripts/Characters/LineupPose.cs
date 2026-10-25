using UnityEngine;

namespace JieGuang
{
    // Test helper: holds a character in one animator state at a fixed normalised time.
    // State and time can be changed from the command line through the static fields.
    public sealed class LineupPose : MonoBehaviour
    {
        public static string State = "Locomotion";
        public static float NormalizedTime = 0.3f;
        public static float Speed;

        Animator animator;
        string applied;
        float appliedTime = -1f, appliedSpeed = -1f;

        void Start() => animator = GetComponent<Animator>();

        void Update()
        {
            if (applied == State && Mathf.Approximately(appliedTime, NormalizedTime) && Mathf.Approximately(appliedSpeed, Speed)) return;
            applied = State;
            appliedTime = NormalizedTime;
            appliedSpeed = Speed;
            animator.SetFloat("Speed", Speed);
            animator.speed = 1f;
            animator.Play(State, 0, NormalizedTime);
            animator.Update(0f);
            animator.speed = 0f;
        }
    }
}
