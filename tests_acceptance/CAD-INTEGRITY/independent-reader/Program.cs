using System.Text.Json;
using ACadSharp.IO;
using ACadSharp.Entities;

if (args.Length < 2) return 2;
if (args[0] == "--fixture") {
    var fixture = new ACadSharp.CadDocument(ACadSharp.ACadVersion.AC1015);
    var curve = new Polyline2D();
    curve.Vertices.Add(new Vertex2D { Location=new CSMath.XYZ(0,0,0),Bulge=0.25 });
    curve.Vertices.Add(new Vertex2D { Location=new CSMath.XYZ(2,1,0),Bulge=0 });
    fixture.Entities.Add(curve);
    DwgWriter.Write(args[1],fixture);
    return 0;
}
var warnings = new Dictionary<string, int>();
var doc = DwgReader.Read(args[0], (sender, note) => {
    var key = note.NotificationType + ": " + note.Message;
    warnings[key] = warnings.GetValueOrDefault(key) + 1;
});
var blocks = doc.BlockRecords.Select(block => new {
    handle = block.Handle.ToString("X"),
    members = block.Entities.Select(e => e.Handle.ToString("X")).ToArray(),
    polylines = block.Entities.OfType<Polyline2D>().Select(line => new {
        handle = line.Handle.ToString("X"),
        vertices = line.Vertices.Select(v => new {
            handle = v.Handle.ToString("X"),
            point = new[] {v.Location.X, v.Location.Y,v.Location.Z},
            flag = (int)v.Flags, bulge = v.Bulge, start_width=v.StartWidth, end_width=v.EndWidth
        })
    }),
    texts = block.Entities.OfType<TextEntity>().Select(t => new {handle=t.Handle.ToString("X"), value=t.Value})
});
File.WriteAllText(args[1],JsonSerializer.Serialize(new {warnings, blocks}));
return 0;
