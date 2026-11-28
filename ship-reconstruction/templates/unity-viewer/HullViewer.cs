using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Threading.Tasks;
using GLTFast;
using UnityEngine;

public class HullViewer : MonoBehaviour
{
    [Serializable] public class Part { public string id,title,group,source,grade,installation,parameters; }
    [Serializable] public class Track { public string node,kind; public float min,max; public Quaternion[] rotations; }
    [Serializable] public class Catalog { public string mode,sha256; public Part[] items; public Track[] tracks; }
    Catalog catalog;
    readonly Dictionary<string,Transform> nodes=new Dictionary<string,Transform>();
    readonly Dictionary<string,Part> parts=new Dictionary<string,Part>();
    readonly Dictionary<string,float> commands=new Dictionary<string,float>();
    readonly Dictionary<string,float> phases=new Dictionary<string,float>();
    readonly List<Material> materials=new List<Material>();
    GameObject model;
    GltfImport importer;
    Camera cam;
    Bounds bounds;
    Vector3 target;
    float distance,yaw=22,pitch=20,cut;
    bool section, hideInternal, busy, error;
    int page;
    string status, selected;
    Vector2 scroll;
    readonly string[] files={"assembly","patches","brackets"};
    readonly string[] titles={"整船 · 假设演示","原图约束开片","局部肘板"};
    public async void Start() {
        cam=gameObject.AddComponent<Camera>();cam.backgroundColor=new Color(.075f,.11f,.16f);
        cam.clearFlags=CameraClearFlags.SolidColor;cam.nearClipPlane=.02f;cam.farClipPlane=1000;
        Application.targetFrameRate=45;
        await Load(0);
        if(Environment.GetCommandLineArgs().Contains("--verify-viewer")) VerifyPlayer();
    }
    public async Task Load(int index) {
        if(busy)return;
        busy=true;error=false;selected="";status="正在核对模型指纹…";page=index;
        try {
            if(model){model.SetActive(false);Destroy(model);}
            foreach(var material in materials)Destroy(material);
            materials.Clear();nodes.Clear();parts.Clear();phases.Clear();importer?.Dispose();importer=null;
            commands.Clear();section=hideInternal=false;
            var dir=Application.streamingAssetsPath;var key=files[index];
            catalog=JsonUtility.FromJson<Catalog>(File.ReadAllText(Path.Combine(dir,key+".json")));
            var expectedModes=new[]{"demo","strict","unregistered_local_demo"};
            if(catalog.mode!=expectedModes[index])throw new InvalidDataException("视图模式与构件目录不匹配");
            var bytes=File.ReadAllBytes(Path.Combine(dir,key+".glb"));
            using(var sha=SHA256.Create())
                if(BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-","").ToLowerInvariant()!=catalog.sha256)
                    throw new InvalidDataException("模型指纹与构件目录不符");
            importer=new GltfImport(deferAgent:new UninterruptedDeferAgent());
            if(!await importer.LoadGltfBinary(bytes))throw new InvalidDataException("GLB 载入失败");
            model=new GameObject("ResearchModel");
            if(!await importer.InstantiateMainSceneAsync(model.transform))throw new InvalidDataException("场景实例化失败");
            foreach(var t in model.GetComponentsInChildren<Transform>())nodes[t.name]=t;
            var shader=Resources.Load<Shader>("ResearchSection");if(!shader)throw new Exception("剖切着色器缺失");
            var palette=new Dictionary<string,Material>();
            foreach(var part in catalog.items){
                if(!nodes.TryGetValue(part.id,out var tr))throw new Exception("目录节点缺失 "+part.id);
                parts[part.id]=part;
                if(!palette.TryGetValue(part.group,out var mat)){
                    mat=new Material(shader);mat.color=part.group=="hull"?new Color(.29f,.54f,.66f):part.group=="decks"?new Color(.72f,.61f,.45f):part.group=="equipment"?new Color(.87f,.52f,.23f):part.group=="structure"?new Color(.33f,.69f,.62f):new Color(.84f,.86f,.85f);
                    palette[part.group]=mat;materials.Add(mat);
                }
                foreach(var rr in tr.GetComponentsInChildren<MeshRenderer>()){
                    rr.sharedMaterials=Enumerable.Repeat(mat,rr.sharedMaterials.Length).ToArray();
                    var mf=rr.GetComponent<MeshFilter>();if(mf && mf.sharedMesh)rr.gameObject.AddComponent<MeshCollider>().sharedMesh=mf.sharedMesh;
                }
            }
            foreach(var tr in catalog.tracks)if(!nodes.ContainsKey(tr.node))throw new Exception("关节缺失 "+tr.node);
            var renderers=model.GetComponentsInChildren<Renderer>();bounds=renderers[0].bounds;
            foreach(var rr in renderers)bounds.Encapsulate(rr.bounds);
            target=bounds.center;distance=Mathf.Max(.5f,bounds.size.magnitude*1.17f);cut=target.x;
            PlaceCamera();ApplySection();status=catalog.items.Length+" 个网格节点  ·  "+catalog.tracks.Length+" 个演示关节";
            Debug.Log("V11 LOAD "+key+" nodes="+catalog.items.Length+" joints="+catalog.tracks.Length+" sha="+catalog.sha256);
        }catch(Exception e){error=true;status=e.Message;Debug.LogException(e);}
        finally{busy=false;}
    }
    void PlaceCamera(){
        cam.transform.position=target+Quaternion.Euler(-pitch,yaw,0)*Vector3.forward*distance;
        cam.transform.LookAt(target);
    }
    void ApplySection(){
        Shader.SetGlobalFloat("_SectionEnabled",section?1:0);Shader.SetGlobalFloat("_SectionX",cut);
        foreach(var x in parts)if(x.Value.group=="structure")nodes[x.Key].gameObject.SetActive(!hideInternal);
    }
    void Pose(float dt){
        foreach(var t in catalog.tracks){
            phases.TryGetValue(t.node,out var angle);
            commands.TryGetValue(t.node,out var command);
            angle=t.kind=="continuous"?Mathf.Repeat(angle+command*6*dt,360):Mathf.Clamp(command,t.min,t.max);phases[t.node]=angle;
            float u=(angle-t.min)/(t.max-t.min)*(t.rotations.Length-1);int k=Mathf.FloorToInt(u);
            var q=Quaternion.Slerp(t.rotations[k],t.rotations[Mathf.Min(k+1,t.rotations.Length-1)],u-k);
            // GLTFast mirrors the glTF X coordinate. Quaternion vector parts transform axially.
            nodes[t.node].localRotation=new Quaternion(q.x,-q.y,-q.z,q.w);
        }
    }
    void Pick(Ray ray){
        foreach(var hit in Physics.RaycastAll(ray).OrderBy(h=>h.distance)){
            if(section && hit.point.x<cut)continue;
            for(Transform t=hit.transform;t;t=t.parent)if(parts.ContainsKey(t.name)){selected=t.name;return;}
        }
    }
    void Update(){
        if(busy||error||catalog==null)return;
        var panel=new Rect(12,12,306,Mathf.Min(Screen.height-24,680));
        if(!panel.Contains(new Vector2(Input.mousePosition.x,Screen.height-Input.mousePosition.y))){
            if(Input.GetMouseButton(1)){yaw+=Input.GetAxis("Mouse X")*3;pitch=Mathf.Clamp(pitch+Input.GetAxis("Mouse Y")*3,-85,85);}
            distance=Mathf.Clamp(distance*Mathf.Exp(-Input.mouseScrollDelta.y*.12f),.1f,500);
            if(Input.GetMouseButtonDown(0))Pick(cam.ScreenPointToRay(Input.mousePosition));
        }
        PlaceCamera();Pose(Time.deltaTime);
    }
    bool fontSet;
    void OnGUI(){
        if(!fontSet){var f=Font.CreateDynamicFontFromOSFont(new[]{"PingFang SC","Arial Unicode MS","Arial"},15);if(f)GUI.skin.font=f;fontSet=true;}
        GUILayout.BeginArea(new Rect(12,12,306,Mathf.Min(Screen.height-24,680)),GUI.skin.box);
        scroll=GUILayout.BeginScrollView(scroll);
        GUILayout.Label("船舶重建研究查看器");GUILayout.Label(status);
        GUI.enabled=!busy;
        for(int i=0;i<files.Length;i++)if(GUILayout.Button(titles[i])){_=Load(i);}
        GUI.enabled=!busy&&!error && catalog!=null;
        if(catalog!=null){
            GUILayout.Label(page==0?"候选安装 · 转速及舵角只用于演示":page==1?"局部开片 · 无封盖和运动授权":"局部坐标 · 横向位置、焊接未知");
            yaw=Slider("环视角",Mathf.Repeat(yaw,360),0,360);
            bool prev=section,hidden=hideInternal;float last=cut;
            section=GUILayout.Toggle(section,"纵向剖切");if(section)cut=Slider("剖面位置（Unity X，m）",cut,bounds.min.x,bounds.max.x);
            hideInternal=GUILayout.Toggle(hideInternal,"隐藏内部结构");
            if(prev!=section || hidden!=hideInternal || last!=cut)ApplySection();
            if(page==0){foreach(var t in catalog.tracks){commands.TryGetValue(t.node,out var command);bool continuous=t.kind=="continuous";commands[t.node]=Slider(t.node+(continuous?" 演示 rpm":" 演示 °"),command,continuous?-60:t.min,continuous?60:t.max);}if(GUILayout.Button("控制归零")){commands.Clear();phases.Clear();}}
            if(parts.TryGetValue(selected??"",out var item)){
                GUILayout.Label(item.title+" · "+item.installation);GUILayout.Label(item.grade);
                GUILayout.Label(item.source);GUILayout.Label(item.parameters);
            }else GUILayout.Label("点击构件查看证据。右键拖动环视，滚轮缩放。");
        }
        GUI.enabled=true;GUILayout.EndScrollView();GUILayout.EndArea();
    }
    static float Slider(string title,float value,float lo,float hi){
        GUILayout.Label(title+"   "+value.ToString("0.0"));return GUILayout.HorizontalSlider(value,lo,hi);
    }
    async void VerifyPlayer(){
        try{
            if(error)throw new Exception(status);
            var holders=catalog.tracks.ToDictionary(t=>t.node,t=>nodes[t.node].localRotation);
            var movingRoots=catalog.tracks.Select(t=>nodes[t.node]).ToArray();
            var fixedBefore=parts.Values.Where(p=>!movingRoots.Any(root=>nodes[p.id].IsChildOf(root)))
                .ToDictionary(p=>p.id,p=>nodes[p.id].localToWorldMatrix);
            foreach(var t in catalog.tracks){commands.Clear();phases.Clear();Pose(0);var before=catalog.tracks.ToDictionary(x=>x.node,x=>nodes[x.node].localRotation);commands[t.node]=t.kind=="continuous"?10:Mathf.Clamp(18,t.min,t.max);Pose(.5f);if(Quaternion.Angle(before[t.node],nodes[t.node].localRotation)<1 || before.Any(k=>k.Key!=t.node && Quaternion.Angle(k.Value,nodes[k.Key].localRotation)>.01f))throw new Exception("独立关节控制失效 "+t.node);}
            commands.Clear();phases.Clear();foreach(var t in catalog.tracks)commands[t.node]=t.kind=="continuous"?10:18;Pose(.5f);
            if(holders.Count==0||holders.Any(k=>Quaternion.Angle(k.Value,nodes[k.Key].localRotation)<1))throw new Exception("关节控制失效");
            if(fixedBefore.Any(k=>k.Value!=nodes[k.Key].localToWorldMatrix))throw new Exception("固定节点随动");
            section=hideInternal=true;cut=bounds.center.x;ApplySection();
            if(parts.Values.Where(p=>p.group=="structure").Any(p=>nodes[p.id].gameObject.activeSelf))throw new Exception("隐藏控制失效");
            section=hideInternal=false;ApplySection();Physics.SyncTransforms();
            for(int y=3;y<=7&&string.IsNullOrEmpty(selected);y++)for(int x=2;x<=8&&string.IsNullOrEmpty(selected);x++)
                Pick(cam.ViewportPointToRay(new Vector3(x/10f,y/10f,0)));
            if(string.IsNullOrEmpty(selected))throw new Exception("点击拾取失效");
            Debug.Log("V11 CONTROL PASS moving="+holders.Count+" isolated="+fixedBefore.Count+" picked="+selected);
            string folder=Environment.GetEnvironmentVariable("MCIS_CAPTURE_DIR");
            if(!string.IsNullOrEmpty(folder)){
                ScreenCapture.CaptureScreenshot(Path.Combine(folder,"整船运行.png"));await Task.Delay(700);
                section=true;cut=bounds.center.x;ApplySection();
                ScreenCapture.CaptureScreenshot(Path.Combine(folder,"整船剖切.png"));await Task.Delay(700);
            }
            await Load(1);if(error||catalog.tracks.Length!=0)throw new Exception("严格模式错配");
            await Load(2);if(error||catalog.tracks.Length!=0)throw new Exception("局部坐标错配");
            Debug.Log("V11 PLAYER PASS");Application.Quit(0);
        }catch(Exception e){Debug.LogException(e);Application.Quit(1);}
    }
}
