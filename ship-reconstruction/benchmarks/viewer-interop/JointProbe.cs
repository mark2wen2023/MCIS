using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Collections;
using UnityEngine;

// Exercises the frozen player's own glTF importer and pose implementation.
public class JointProbe : MonoBehaviour {
    [Serializable] public class TestPoint { public string node; public float angle,x,y,z; }
    [Serializable] public class Oracle { public TestPoint[] cases; public string fixedNode; public float tolerance_m; }
    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Launch() {
        if(Environment.GetCommandLineArgs().Contains("--verify-world"))
            new GameObject("CoordinateWitness").AddComponent<JointProbe>();
    }
    IEnumerator Start() {
        var viewer=FindFirstObjectByType<HullViewer>();
        var flags=BindingFlags.NonPublic|BindingFlags.Instance;
        var type=typeof(HullViewer);
        for(int i=0;i<1200 && (viewer==null || type.GetField("model",flags).GetValue(viewer)==null ||
            (bool)type.GetField("busy",flags).GetValue(viewer));i++) {
            yield return null; viewer=FindFirstObjectByType<HullViewer>();
        }
        try {
            var root=(GameObject)type.GetField("model",flags).GetValue(viewer);
            var nodes=root.GetComponentsInChildren<Transform>().ToDictionary(t=>t.name,t=>t);
            var oracle=JsonUtility.FromJson<Oracle>(File.ReadAllText(Path.Combine(Application.streamingAssetsPath,"oracle.json")));
            var fixedMatrix=nodes["fixed"].localToWorldMatrix;
            foreach(var c in oracle.cases) {
                type.GetField("helm",flags).SetValue(viewer,c.angle);
                type.GetMethod("Pose",flags).Invoke(viewer,new object[]{0f});
                var p=nodes[c.node].position;
                var error=Vector3.Distance(p,new Vector3(-c.x,c.y,c.z));
                Debug.Log(FormattableString.Invariant($"WORLD {c.node} {c.angle} {p.x:R} {p.y:R} {p.z:R} {error:R}"));
                if(error>oracle.tolerance_m || fixedMatrix!=nodes["fixed"].localToWorldMatrix)
                    throw new Exception("world coordinate or fixed-node mismatch");
            }
            Debug.Log("WORLD PASS");Application.Quit(0);
        }catch(Exception e){Debug.LogException(e);Application.Quit(1);}
    }
}
