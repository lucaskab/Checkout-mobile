using System;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEngine;
using UnityEngine.AI;

// Run after applying any app snapshot in Play Mode; never mutates saved game state.
public static class CheckoutCityValidation
{
    public static string ValidateRuntime()
    {
        if(!Application.isPlaying)throw new InvalidOperationException("Run in Play Mode with a snapshot.");
        var layout=UnityEngine.Object.FindAnyObjectByType<CheckoutMarketLayout>();
        var streets=UnityEngine.Object.FindAnyObjectByType<CheckoutCityStreets>();
        var origin=new Vector3(-1.75f,.15f,-11.5f);
        foreach(var point in streets.entrances.Concat(streets.patrolPoints))
        {
            var path=new NavMeshPath();
            Require(NavMesh.CalculatePath(origin,point,NavMesh.AllAreas,path)&&path.status==NavMeshPathStatus.PathComplete,"Unreachable city destination "+point);
        }
        bool Walkable(float x,float z)=>NavMesh.SamplePosition(new Vector3(x,.15f,z),out _, .15f,NavMesh.AllAreas);
        foreach(float x in new[]{-23.5f,23.5f})
        {
            foreach(float z in new[]{-21f,-10f,24.5f,35.5f})Require(Walkable(x,z),"Missing painted crossing");
            foreach(float z in new[]{-19.5f,-11.5f,26f,34f})Require(!Walkable(x,z),"Unmarked corner shortcut");
        }
        foreach(float z in new[]{-15.5f,30f})
        {
            foreach(float x in new[]{-29f,-18f,18f,29f})Require(Walkable(x,z),"Missing painted crossing");
            foreach(float x in new[]{-27.5f,-19.5f,19.5f,27.5f})Require(!Walkable(x,z),"Unmarked corner shortcut");
        }
        var parking=UnityEngine.Object.FindAnyObjectByType<CheckoutParkingSpaces>();
        int spaces=layout.State.parking?(layout.State.stage>=3?5:3):0;
        Require(parking.spaces.Count(s=>s.activeSelf)==spaces,"Incorrect visible parking capacity");
        var traffic=UnityEngine.Object.FindAnyObjectByType<CheckoutCityTraffic>();Require(traffic.vehicles.Length==5,"Missing parking car pool");
        if(spaces>0)Require(traffic.enabled&&traffic.Capacity==spaces,"Parking traffic disabled or capacity mismatch");
        var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        var header=world.Find("City Detail Repairs/Clean entrance frame/Entrance header").GetComponent<Renderer>().bounds;
        foreach(string name in new[]{"Anim_Door_Left","Anim_Door_Right"})
        {
            var leaf=world.Find(name).GetComponentInChildren<Renderer>().bounds;
            Require(Mathf.Abs(header.min.y-leaf.max.y)<.04f,"Door leaf/header height mismatch");
        }
        var appearances=UnityEngine.Object.FindObjectsByType<CheckoutCityAppearance>(FindObjectsInactive.Include).Select(a=>a.Appearance).Where(a=>a!=null).Distinct().Count();
        Require(appearances>=5,"City character variation missing");
        Require(UnityEngine.Object.FindObjectsByType<Light>().Count(l=>l.type==LightType.Spot)>=28,"Streetlight effects missing");
        return "CITY_VALIDATED stage="+layout.State.stage+" spaces="+spaces+" appearances="+appearances+" crossings=16";
    }
    static void Require(bool condition,string message){if(!condition)throw new InvalidOperationException(message);}
}
