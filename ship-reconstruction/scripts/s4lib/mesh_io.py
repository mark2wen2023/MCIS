"""以双精度保存船轴顶点，并从实际输出文件回读后发布。"""
import os
from pathlib import Path
import tempfile
import numpy as np
import trimesh


def write_solid(path,mesh):
    vertices=np.asarray(mesh.vertices,dtype="<f8"); faces=np.asarray(mesh.faces,dtype="<i4")
    if not np.isfinite(vertices).all():raise ValueError("输出包含非有限顶点")
    header=("ply\nformat binary_little_endian 1.0\n"
            f"element vertex {len(vertices)}\nproperty double x\nproperty double y\nproperty double z\n"
            f"element face {len(faces)}\nproperty list uchar int vertex_indices\nend_header\n")
    packed=np.empty(len(faces),dtype=[("count","u1"),("indices","<i4",(3,))])
    packed["count"]=3;packed["indices"]=faces
    with tempfile.NamedTemporaryFile(dir=path.parent,suffix=".ply",delete=False) as f:
        tmp=Path(f.name)
        try:
            f.write(header.encode("ascii"));f.write(vertices.tobytes());f.write(packed.tobytes());f.flush()
            reread=trimesh.load_mesh(tmp,process=False)
            if not np.array_equal(vertices,reread.vertices) or not np.array_equal(faces,reread.faces):
                raise ValueError("PLY回读的顶点或面与验收实体不一致")
            os.replace(tmp,path)
        finally:
            tmp.unlink(missing_ok=True)
