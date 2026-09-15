using UnityEngine;

namespace MarketDay
{
    public class MarketChickenAnimator : MonoBehaviour
    {
        public Animation animationPlayer;

        MarketSimulation simulation;
        Vector3 home;
        Quaternion restRotation;
        string current;
        float clock;
        float offset;

        void Start()
        {
            simulation = FindAnyObjectByType<MarketSimulation>();
            if (!animationPlayer) animationPlayer = GetComponentInChildren<Animation>();
            home = transform.position;
            restRotation = transform.rotation;
            offset = Mathf.Abs(name.GetHashCode() % 97) * 0.19f;
            Play("Idle");
        }

        void Update()
        {
            if (!animationPlayer) return;

            var rate = simulation ? simulation.speed : 1f;
            clock += Time.deltaTime * rate;
            var cycle = Mathf.Repeat(clock + offset, 12f);

            if (cycle < 5f)
            {
                var pathTime = (clock + offset) * 0.75f;
                var target = home + new Vector3(Mathf.Sin(pathTime) * 0.22f, 0f, Mathf.Cos(pathTime * 0.83f) * 0.18f);
                var direction = target - transform.position;
                direction.y = 0f;
                if (direction.sqrMagnitude > 0.0001f)
                {
                    transform.rotation = Quaternion.Slerp(transform.rotation, Quaternion.LookRotation(-direction), Time.deltaTime * 6f * rate);
                    transform.position = Vector3.MoveTowards(transform.position, target, Time.deltaTime * 0.16f * rate);
                }
                Play("Walk", rate * 0.9f);
            }
            else if (cycle < 7.4f)
            {
                transform.rotation = Quaternion.Slerp(transform.rotation, restRotation, Time.deltaTime * 0.8f * rate);
                Play("Idle", rate);
            }
            else if (cycle < 10.2f)
            {
                Play("Eat", rate);
            }
            else
            {
                Play("Idle", rate);
            }
        }

        void Play(string clip, float speed = 1f)
        {
            if (!animationPlayer[clip]) return;
            animationPlayer[clip].speed = speed;
            if (current == clip) return;
            current = clip;
            animationPlayer.CrossFade(clip, 0.16f);
        }
    }
}
