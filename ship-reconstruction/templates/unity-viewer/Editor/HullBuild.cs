using System;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build.Reporting;
using UnityEngine;
public static class HullBuild {
    public static void Build(){
        var scene=EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
        new GameObject("HullViewer").AddComponent<HullViewer>();
        EditorSceneManager.SaveScene(scene,"Assets/HullViewer.unity");
        var sh=Shader.Find("glTF/PbrMetallicRoughness");
        if(sh && !AssetDatabase.LoadAssetAtPath<Material>("Assets/Resources/RuntimePbr.mat"))
            AssetDatabase.CreateAsset(new Material(sh),"Assets/Resources/RuntimePbr.mat");
        PlayerSettings.SetArchitecture(UnityEditor.Build.NamedBuildTarget.Standalone,1);
        PlayerSettings.fullScreenMode=FullScreenMode.Windowed;
        PlayerSettings.runInBackground=true;
        PlayerSettings.productName="MCIS Ship Research Viewer";
        var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{
            scenes=new[]{"Assets/HullViewer.unity"},locationPathName=Environment.GetEnvironmentVariable("MCIS_VIEWER_OUT"),
            target=BuildTarget.StandaloneOSX,options=BuildOptions.None});
        if(result.summary.result!=BuildResult.Succeeded)throw new Exception(result.summary.result.ToString());
    }
}
