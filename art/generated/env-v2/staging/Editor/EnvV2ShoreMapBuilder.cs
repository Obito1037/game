#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using Object = UnityEngine.Object;

namespace JieGuang.EnvironmentTools
{
    /// <summary>
    /// CPU-only, explicitly invoked coast distance bake from the passed Island's real meshes.
    /// No physics queries, scene mutation, RenderSettings, material binding or project-wide search.
    /// Prefer the terrain/cliff intersection with the actual sea plane; fallback is welded ground boundary.
    /// Texture R = min(nearest world-XZ contour distance in metres / 8, 1).
    /// </summary>
    public static class EnvV2ShoreMapBuilder
    {
        public const string OutputRoot = "Assets/JieGuang/Environment/Generated/V2ShoreMaps";
        public const float DistanceRangeMetres = 8f;
        const float PlaneEpsilon = .0001f;
        const float WeldMetres = .001f;
        const float GridMetres = 8f;

        [Serializable] public sealed class Check { public string name; public bool passed; public string detail; }
        [Serializable] public sealed class Report
        {
            public string status, generatedUtc, unityVersion, method, textureAssetPath, reportAssetPath;
            public string distanceEncoding = "R linear UNorm8 = clamp(unsigned world-XZ distance to actual coast / 8 metres, 0, 1)";
            public float seaHeight, distanceRangeMetres = DistanceRangeMetres, actualPadding;
            public int resolution, mipCount, sourceTriangles, segments, degenerateSegmentsSkipped, duplicateSegmentsSkipped;
            public int nonDegreeTwoContourVertices, nearShorePixels, saturatedPixels, intermediatePixels;
            public Vector4 worldRect;
            public Vector2 sourceMinXZ, sourceMaxXZ;
            public bool contourClosed;
            public List<string> sources = new List<string>();
            public List<string> warnings = new List<string>();
            public List<Check> checks = new List<Check>();
        }
        public sealed class Result
        {
            public Texture2D texture;
            public Vector4 worldRect;
            public Report report;
        }
        struct Segment { public Vector2 a,b; }
        struct VertexKey : IEquatable<VertexKey>
        {
            public int x,y,z;
            public VertexKey(Vector3 p){x=Mathf.RoundToInt(p.x/WeldMetres);y=Mathf.RoundToInt(p.y/WeldMetres);z=Mathf.RoundToInt(p.z/WeldMetres);}
            public bool Equals(VertexKey o)=>x==o.x&&y==o.y&&z==o.z;
            public override bool Equals(object o)=>o is VertexKey v&&Equals(v);
            public override int GetHashCode(){unchecked{return(x*397^y)*397^z;}}
        }
        struct EdgeKey : IEquatable<EdgeKey>
        {
            public int a,b;
            public EdgeKey(int x,int y){a=Mathf.Min(x,y);b=Mathf.Max(x,y);}
            public bool Equals(EdgeKey o)=>a==o.a&&b==o.b;
            public override bool Equals(object o)=>o is EdgeKey e&&Equals(e);
            public override int GetHashCode(){unchecked{return a*397^b;}}
        }
        sealed class Source
        {
            public MeshFilter filter;
            public Vector3[] worldVertices;
            public int[] triangles;
        }

        /// <param name="islandRoot">Only this island's direct Terrain subtree is read.</param>
        /// <param name="seaHeight">World Y of the actual flat NightSea mesh, normally -.16m.</param>
        /// <param name="resolution">256 or 512, square texture with explicit non-square world rectangle.</param>
        /// <param name="paddingMetres">Requested contour margin; raised if needed to guarantee white map borders.</param>
        public static Result Bake(GameObject islandRoot, float seaHeight = -.16f, int resolution = 256, float paddingMetres = 9f)
        {
            if(islandRoot==null)throw new ArgumentNullException(nameof(islandRoot));
            if(resolution!=256&&resolution!=512)throw new ArgumentException("Shore map supports 256 or 512 pixels.");
            if(!Finite(seaHeight)||!Finite(paddingMetres)||paddingMetres<0||paddingMetres>50)throw new ArgumentException("Sea height and padding must be finite, padding in 0..50 metres.");
            Transform terrain=DirectTerrain(islandRoot.transform);
            var report=new Report {generatedUtc=DateTime.UtcNow.ToString("O"),unityVersion=Application.unityVersion,seaHeight=seaHeight,resolution=resolution,status="reading-owned-coast-geometry"};
            var sources=new List<Source>();
            foreach(string name in new[]{"IslandGround","CoastalCliff"})
            {
                MeshFilter[] matches=terrain.GetComponentsInChildren<MeshFilter>(true).Where(f=>f.name==name).ToArray();
                if(matches.Length!=1)throw new InvalidOperationException("Expected exactly one owned Terrain mesh named "+name+", found "+matches.Length+".");
                MeshFilter mf=matches[0];Mesh mesh=mf.sharedMesh;
                if(mesh==null||!mesh.isReadable)throw new InvalidOperationException(name+" must have a readable mesh. This tool does not change import settings or substitute a hand-drawn footprint.");
                if(mesh.subMeshCount<1)throw new InvalidOperationException(name+" has no triangle submeshes.");
                for(int i=0;i<mesh.subMeshCount;i++)if(mesh.GetTopology(i)!=MeshTopology.Triangles)throw new InvalidOperationException("Coast source contains non-triangle topology.");
                Vector3[] vertices=mesh.vertices;
                for(int i=0;i<vertices.Length;i++)
                {
                    vertices[i]=mf.transform.TransformPoint(vertices[i]);
                    if(!Finite(vertices[i].x)||!Finite(vertices[i].y)||!Finite(vertices[i].z))throw new InvalidOperationException("Non-finite source mesh coordinates.");
                }
                var source=new Source {filter=mf,worldVertices=vertices,triangles=mesh.triangles};sources.Add(source);
                report.sourceTriangles+=source.triangles.Length/3;
                report.sources.Add(PathFromRoot(islandRoot.transform,mf.transform)+" | "+AssetDatabase.GetAssetPath(mesh)+" | "+mesh.name);
            }
            var raw=new List<Segment>();
            foreach(Source source in sources)AppendWaterlineSegments(source,seaHeight,raw);
            report.method="actual-terrain-cliff-triangle-intersection-at-sea-height";
            if(raw.Count<3)
            {
                raw.Clear();AppendGroundBoundary(sources.Single(s=>s.filter.name=="IslandGround"),raw);
                report.method="welded-IslandGround-boundary-projected-to-world-XZ";
                report.warnings.Add("Fewer than three waterline segments intersect the requested sea Y. Used actual welded ground mesh boundary, not an inferred circle or walkable boundary. Check cliff/sea contact visually.");
            }
            List<Segment> segments=Deduplicate(raw,report);
            if(segments.Count<3)throw new InvalidOperationException("No usable actual coast contour; refuse to create a plausible but invented shoreline map.");
            report.segments=segments.Count;report.contourClosed=report.nonDegreeTwoContourVertices==0;
            if(!report.contourClosed)report.warnings.Add("Contour has "+report.nonDegreeTwoContourVertices+" vertices with degree other than 2 after 1mm welding. Map reflects the actual partial contour; inspect mesh seams rather than treating this as watertight geometry.");
            Vector2 minimum=segments[0].a,maximum=segments[0].a;
            foreach(Segment s in segments){minimum=Vector2.Min(minimum,Vector2.Min(s.a,s.b));maximum=Vector2.Max(maximum,Vector2.Max(s.a,s.b));}
            Vector2 span=maximum-minimum;
            if(span.x<.5f||span.y<.5f||span.x>1000||span.y>1000)throw new InvalidOperationException("Coast span is implausible for this island. Confirm source scale and sea plane.");
            // At least one complete pixel beyond the 8m clamp radius keeps mip borders stable.
            float padding=Mathf.Max(paddingMetres,DistanceRangeMetres+Mathf.Max(span.x,span.y)/resolution+.15f);
            Vector2 mapMin=minimum-Vector2.one*padding,mapSize=span+Vector2.one*(padding*2);
            var rect=new Vector4(mapMin.x,mapMin.y,mapSize.x,mapSize.y);
            report.worldRect=rect;report.actualPadding=padding;report.sourceMinXZ=minimum;report.sourceMaxXZ=maximum;
            Dictionary<Vector2Int,List<int>> grid=BuildDistanceGrid(segments);
            var pixels=new byte[resolution*resolution];
            bool borderWhite=true;
            for(int z=0;z<resolution;z++)for(int x=0;x<resolution;x++)
            {
                Vector2 p=mapMin+new Vector2((x+.5f)/resolution*mapSize.x,(z+.5f)/resolution*mapSize.y);
                float distance=NearestDistance(p,segments,grid);
                byte encoded=(byte)Mathf.Clamp(Mathf.RoundToInt(distance/DistanceRangeMetres*255),0,255);
                pixels[z*resolution+x]=encoded;
                if(distance<1.35f)report.nearShorePixels++;
                if(encoded==255)report.saturatedPixels++;else if(encoded>0)report.intermediatePixels++;
                if((x==0||z==0||x==resolution-1||z==resolution-1)&&encoded!=255)borderWhite=false;
            }
            Texture2D texture=null;
            try
            {
                texture=new Texture2D(resolution,resolution,TextureFormat.R8,true,true) {
                    name="ShoreDistance_R8_Linear",wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Trilinear,anisoLevel=0
                };
                texture.SetPixelData(pixels,0);texture.Apply(true,false);
                report.mipCount=texture.mipmapCount;
                Add(report,"linear-data",!GraphicsFormatUtility.IsSRGBFormat(texture.graphicsFormat),"GraphicsFormat="+texture.graphicsFormat+"; R is distance data, not albedo.");
                Add(report,"clamp-and-mips",texture.wrapMode==TextureWrapMode.Clamp&&texture.mipmapCount>1,"Trilinear sampling with generated linear mip chain.");
                Add(report,"saturated-outer-border",borderWhite,"All outer texels are 8m or more from coast; clamp cannot introduce a distant false shore.");
                Add(report,"nontrivial-distance-field",report.nearShorePixels>0&&report.intermediatePixels>0&&report.saturatedPixels>0,"Near shore, transition and saturated distances all represented.");
                Add(report,"valid-world-rectangle",rect.z>0&&rect.w>0,"_ShoreRect=(min world X,min world Z,width metres,depth metres). Pixel Y increases with world Z.");
                if(report.checks.Any(c=>!c.passed))throw new InvalidOperationException("Shore data validation failed: "+string.Join(", ",report.checks.Where(c=>!c.passed).Select(c=>c.name)));
                string generation=OutputRoot+"/ShoreGeneration_"+DateTime.UtcNow.ToString("yyyyMMdd_HHmmss_fffffff");
                EnsureFolder(generation);
                report.textureAssetPath=generation+"/ShoreDistance_R8_Linear.asset";
                report.reportAssetPath=generation+"/shore-report.json";
                if(AssetDatabase.LoadMainAssetAtPath(report.textureAssetPath)!=null)throw new InvalidOperationException("Refusing to overwrite a previously generated distance texture.");
                AssetDatabase.CreateAsset(texture,report.textureAssetPath);AssetDatabase.SaveAssetIfDirty(texture);
                report.status=report.contourClosed?"baked-awaiting-sea-visual-verification":"baked-with-open-contour-warning-awaiting-mesh-and-sea-verification";
                report.warnings.Add("Unsigned coast distance, not bathymetry or a land mask. It does not change sea/terrain geometry and is not automatically bound to any material.");
                report.warnings.Add("No live Unity shader compile, screenshot, frame-time or WebGL verification is implied by this CPU bake.");
                File.WriteAllText(ProjectFile(report.reportAssetPath),JsonUtility.ToJson(report,true),new System.Text.UTF8Encoding(false));
                AssetDatabase.ImportAsset(report.reportAssetPath,ImportAssetOptions.ForceSynchronousImport);
                return new Result {texture=texture,worldRect=rect,report=report};
            }
            catch
            {
                if(texture!=null&&!EditorUtility.IsPersistent(texture))Object.DestroyImmediate(texture);
                throw;
            }
        }

        static void AppendWaterlineSegments(Source source,float seaY,List<Segment> output)
        {
            var intersections=new List<Vector3>(3);
            for(int t=0;t<source.triangles.Length;t+=3)
            {
                Vector3 a=source.worldVertices[source.triangles[t]],b=source.worldVertices[source.triangles[t+1]],c=source.worldVertices[source.triangles[t+2]];
                if(Mathf.Abs(a.y-seaY)<PlaneEpsilon&&Mathf.Abs(b.y-seaY)<PlaneEpsilon&&Mathf.Abs(c.y-seaY)<PlaneEpsilon)continue;
                intersections.Clear();IntersectEdge(a,b,seaY,intersections);IntersectEdge(b,c,seaY,intersections);IntersectEdge(c,a,seaY,intersections);
                if(intersections.Count<2)continue;
                float best=0;Vector3 p=intersections[0],q=intersections[1];
                for(int i=0;i<intersections.Count;i++)for(int j=i+1;j<intersections.Count;j++)
                {float d=(intersections[i]-intersections[j]).sqrMagnitude;if(d>best){best=d;p=intersections[i];q=intersections[j];}}
                if(best>PlaneEpsilon*PlaneEpsilon)output.Add(new Segment{a=new Vector2(p.x,p.z),b=new Vector2(q.x,q.z)});
            }
        }
        static void IntersectEdge(Vector3 a,Vector3 b,float y,List<Vector3> points)
        {
            float da=a.y-y,db=b.y-y;
            if(Mathf.Abs(da)<PlaneEpsilon)AddUnique(points,new Vector3(a.x,y,a.z));
            if(Mathf.Abs(db)<PlaneEpsilon)AddUnique(points,new Vector3(b.x,y,b.z));
            if((da>PlaneEpsilon&&db<-PlaneEpsilon)||(da<-PlaneEpsilon&&db>PlaneEpsilon))AddUnique(points,Vector3.LerpUnclamped(a,b,da/(da-db)));
        }
        static void AddUnique(List<Vector3> points,Vector3 p)
        {if(!points.Any(q=>(q-p).sqrMagnitude<PlaneEpsilon*PlaneEpsilon))points.Add(p);}
        static void AppendGroundBoundary(Source ground,List<Segment> output)
        {
            var welded=new Dictionary<VertexKey,int>();var points=new List<Vector3>();var indices=new int[ground.worldVertices.Length];
            for(int i=0;i<indices.Length;i++)
            {
                VertexKey key=new VertexKey(ground.worldVertices[i]);
                if(!welded.TryGetValue(key,out int index)){index=points.Count;welded.Add(key,index);points.Add(ground.worldVertices[i]);}indices[i]=index;
            }
            var edges=new Dictionary<EdgeKey,int>();
            for(int t=0;t<ground.triangles.Length;t+=3)
            {
                int a=indices[ground.triangles[t]],b=indices[ground.triangles[t+1]],c=indices[ground.triangles[t+2]];
                if(a==b||b==c||c==a)continue;
                CountEdge(edges,new EdgeKey(a,b));CountEdge(edges,new EdgeKey(b,c));CountEdge(edges,new EdgeKey(c,a));
            }
            foreach(var edge in edges)if(edge.Value==1)
            {Vector3 a=points[edge.Key.a],b=points[edge.Key.b];output.Add(new Segment{a=new Vector2(a.x,a.z),b=new Vector2(b.x,b.z)});}
        }
        static void CountEdge(Dictionary<EdgeKey,int> edges,EdgeKey edge){edges.TryGetValue(edge,out int count);edges[edge]=count+1;}
        static List<Segment> Deduplicate(List<Segment> raw,Report report)
        {
            var ids=new Dictionary<VertexKey,int>();var points=new List<Vector2>();var edges=new HashSet<EdgeKey>();var result=new List<Segment>();
            foreach(Segment segment in raw)
            {
                int a=ContourPointId(segment.a,ids,points),b=ContourPointId(segment.b,ids,points);
                if(a==b||(segment.a-segment.b).sqrMagnitude<PlaneEpsilon*PlaneEpsilon){report.degenerateSegmentsSkipped++;continue;}
                if(!edges.Add(new EdgeKey(a,b))){report.duplicateSegmentsSkipped++;continue;}
                result.Add(new Segment{a=points[a],b=points[b]});
            }
            var degrees=new Dictionary<int,int>();foreach(EdgeKey edge in edges){degrees.TryGetValue(edge.a,out int a);degrees[edge.a]=a+1;degrees.TryGetValue(edge.b,out int b);degrees[edge.b]=b+1;}
            report.nonDegreeTwoContourVertices=degrees.Values.Count(d=>d!=2);
            return result;
        }
        static int ContourPointId(Vector2 p,Dictionary<VertexKey,int> ids,List<Vector2> points)
        {
            VertexKey key=new VertexKey(new Vector3(p.x,0,p.y));
            if(!ids.TryGetValue(key,out int id)){id=points.Count;ids.Add(key,id);points.Add(p);}return id;
        }
        static Dictionary<Vector2Int,List<int>> BuildDistanceGrid(List<Segment> segments)
        {
            var grid=new Dictionary<Vector2Int,List<int>>();
            for(int i=0;i<segments.Count;i++)
            {
                Vector2 min=Vector2.Min(segments[i].a,segments[i].b)-Vector2.one*DistanceRangeMetres;
                Vector2 max=Vector2.Max(segments[i].a,segments[i].b)+Vector2.one*DistanceRangeMetres;
                for(int x=Mathf.FloorToInt(min.x/GridMetres);x<=Mathf.FloorToInt(max.x/GridMetres);x++)
                    for(int z=Mathf.FloorToInt(min.y/GridMetres);z<=Mathf.FloorToInt(max.y/GridMetres);z++)
                    {var key=new Vector2Int(x,z);if(!grid.TryGetValue(key,out List<int> bucket))grid[key]=bucket=new List<int>();bucket.Add(i);}
            }
            return grid;
        }
        static float NearestDistance(Vector2 p,List<Segment> segments,Dictionary<Vector2Int,List<int>> grid)
        {
            var key=new Vector2Int(Mathf.FloorToInt(p.x/GridMetres),Mathf.FloorToInt(p.y/GridMetres));
            if(!grid.TryGetValue(key,out List<int> indices))return DistanceRangeMetres;
            float bestSquared=DistanceRangeMetres*DistanceRangeMetres;
            foreach(int i in indices)
            {Segment s=segments[i];Vector2 d=s.b-s.a;float t=Mathf.Clamp01(Vector2.Dot(p-s.a,d)/Mathf.Max(d.sqrMagnitude,1e-12f));bestSquared=Mathf.Min(bestSquared,(p-s.a-d*t).sqrMagnitude);}
            return Mathf.Sqrt(bestSquared);
        }
        static Transform DirectTerrain(Transform root)
        {Transform found=null;foreach(Transform t in root)if(t.name=="Terrain"){if(found!=null)throw new InvalidOperationException("Duplicate direct Terrain children.");found=t;}if(found==null)throw new InvalidOperationException("Passed island has no direct Terrain subtree.");return found;}
        static string PathFromRoot(Transform root,Transform t)
        {var names=new List<string>();for(Transform p=t;p!=root;p=p.parent){if(p==null)throw new InvalidOperationException("Source escaped the passed island.");names.Add(p.name);}names.Reverse();return string.Join("/",names);}
        static bool Finite(float n)=>!float.IsNaN(n)&&!float.IsInfinity(n);
        static void Add(Report r,string name,bool passed,string detail)=>r.checks.Add(new Check{name=name,passed=passed,detail=detail});
        static string ProjectFile(string path)=>Path.GetFullPath(Path.Combine(Path.GetDirectoryName(Application.dataPath),path));
        static void EnsureFolder(string path)
        {
            if(!path.StartsWith(OutputRoot+"/ShoreGeneration_",StringComparison.Ordinal)||path.Contains(".."))throw new InvalidOperationException("Refusing non-owned output folder.");
            string[] parts=path.Split('/');string current=parts[0];for(int i=1;i<parts.Length;i++){string next=current+"/"+parts[i];if(!AssetDatabase.IsValidFolder(next))AssetDatabase.CreateFolder(current,parts[i]);current=next;}
        }
    }
}
#endif
