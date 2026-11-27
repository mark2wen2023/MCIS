import sys
import tempfile
import unittest
from pathlib import Path
import trimesh
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from s4lib.mesh_io import write_solid

class MeshFile(unittest.TestCase):
    def test_large_offset_thin_plate_roundtrip(self):
        m=trimesh.creation.box([.0005,.5,.75]);m.apply_translation([16000.,0,0])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"thin.ply";write_solid(path,m)
            r=trimesh.load_mesh(path,process=False)
            np.testing.assert_array_equal(r.vertices,m.vertices)
            self.assertGreater(r.volume,0.)
