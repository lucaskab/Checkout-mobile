using UnityEngine;

namespace MarketDay
{
    [RequireComponent(typeof(Camera))]
    public class MarketSharpness : MonoBehaviour
    {
        [Range(0,1)] public float strength=.38f;
        public Shader shader;
        Material effect;
        void OnRenderImage(RenderTexture source,RenderTexture destination)
        {
            if(!shader||!shader.isSupported){Graphics.Blit(source,destination);return;}
            if(!effect)effect=new Material(shader){hideFlags=HideFlags.HideAndDontSave};
            effect.SetFloat("_Strength",strength);Graphics.Blit(source,destination,effect);
        }
        void OnDestroy(){if(effect)Destroy(effect);}
    }
}
