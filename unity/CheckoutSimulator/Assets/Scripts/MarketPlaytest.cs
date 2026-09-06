using System;
using System.Collections;
using System.IO;
using UnityEngine;

namespace MarketDay
{
    // Opt-in player test. It never changes the player's normal save.
    public class MarketPlaytest : MonoBehaviour
    {
        IEnumerator Start()
        {
            var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"--market-qa");
            if(at<0||at+1>=args.Length)yield break;
            string folder=args[at+1];Directory.CreateDirectory(folder);
            Debug.Log("MARKET_QA_STARTED");
            var sim=FindAnyObjectByType<MarketSimulation>();
            while(sim==null||sim.Economy==null){yield return null;sim=FindAnyObjectByType<MarketSimulation>();}
            yield return new WaitForSeconds(1);
            sim.quietCapture=true;sim.OpenStore();sim.Order(0);sim.QueueRefill(0);sim.speed=2;
            yield return new WaitForSeconds(14);
            Capture(sim,Path.Combine(folder,"08-living-gameplay.png"));
            int overlaps=0;for(int sample=0;sample<360;sample++){overlaps=Mathf.Max(overlaps,sim.CrowdOverlapCount());yield return new WaitForSeconds(.25f);}
            bool passed=sim.Economy.served>0&&sim.Economy.delivered>=20&&sim.Economy.restocked>0&&sim.Economy.Valid();
            int routes=0;foreach(var p in sim.browse)if(sim.Route(MarketSimulation.P(-1.75,-8.5),p).Count>0)routes++;
            passed&=routes==5;
            passed&=sim.Route(MarketSimulation.P(4,9.2),sim.browse[0]).Count>0;
            passed&=overlaps==0&&sim.CustomersServedAtLeastOnce()==5;
            passed&=MarketCharacterAnimator.shelfActions>0&&MarketCharacterAnimator.sectorActions>0&&MarketCharacterAnimator.paymentActions>0;
            File.WriteAllText(Path.Combine(folder,"movement-validation.txt"),"Shelf / sector / payment animation starts: "+MarketCharacterAnimator.shelfActions+" / "+MarketCharacterAnimator.sectorActions+" / "+MarketCharacterAnimator.paymentActions+"\nMaximum body overlaps: "+overlaps+"\nDistinct customers completing checkout: "+sim.CustomersServedAtLeastOnce()+"/5\n"+sim.CrowdDiagnostics());
            File.WriteAllText(Path.Combine(folder,"playtest-report.json"),"{\"passed\":"+(passed?"true":"false")+",\"reachableDepartments\":"+routes+",\"gameTime\":"+Time.time.ToString(System.Globalization.CultureInfo.InvariantCulture)+",\"economy\":"+JsonUtility.ToJson(sim.Economy)+"}");
            Debug.Log(passed?"MARKET_PLAYER_TEST_OK":"MARKET_PLAYER_TEST_FAILED");
            sim.speed=1;sim.hud.DepartmentPanel(0);
            yield return new WaitForSeconds(.5f);Capture(sim,Path.Combine(folder,"09-department-detail.png"));
            yield return new WaitForSeconds(1);sim.hud.ClosePanel();
            sim.hud.gameObject.SetActive(false);sim.speed=1;
            var focus=new Vector3(-.5f,.5f,-1.5f);sim.view.transform.position=focus+new Vector3(28,33,-38);sim.view.transform.LookAt(focus);sim.view.orthographicSize=7.8f;
            string frames=Path.GetFullPath(Path.Combine(folder,"../work/movement-frames"));Directory.CreateDirectory(frames);
            Time.captureFramerate=20;
            for(int frame=0;frame<120;frame++){yield return null;CaptureFrame(sim.view,Path.Combine(frames,frame.ToString("D4")+".png"));}
            Time.captureFramerate=0;sim.hud.gameObject.SetActive(true);sim.HomeCamera();
            if(Application.isBatchMode)Application.Quit(passed?0:1);
        }
        static void CaptureFrame(Camera cam,string path)
        {
            var old=cam.targetTexture;var active=RenderTexture.active;var rt=new RenderTexture(960,600,24){antiAliasing=4};cam.targetTexture=rt;cam.Render();RenderTexture.active=rt;
            var image=new Texture2D(960,600,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,960,600),0,0);image.Apply();File.WriteAllBytes(path,image.EncodeToPNG());cam.targetTexture=old;RenderTexture.active=active;Destroy(image);Destroy(rt);
        }
        static void Capture(MarketSimulation sim,string path)
        {
            var cam=sim.view;var old=cam.targetTexture;var active=RenderTexture.active;
            var rt=new RenderTexture(1800,1125,24){antiAliasing=4};cam.targetTexture=rt;
            sim.hud.Relayout();sim.hud.Refresh();Canvas.ForceUpdateCanvases();cam.Render();RenderTexture.active=rt;
            var image=new Texture2D(rt.width,rt.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,rt.width,rt.height),0,0);image.Apply();File.WriteAllBytes(path,image.EncodeToPNG());
            cam.targetTexture=old;RenderTexture.active=active;Destroy(image);Destroy(rt);sim.hud.Relayout();
        }
    }
}

