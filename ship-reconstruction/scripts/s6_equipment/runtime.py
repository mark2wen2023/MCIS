"""Research-only incremental motion; no dynamics or operating authorization."""
import math
import numpy as np
from trimesh.transformations import rotation_matrix, translation_matrix

class Runtime:
    def __init__(self, scene, config):
        self.scene=scene
        self.joints={j['id']:j for j in config['joints']}
        if len(self.joints)!=len(config['joints']): raise ValueError('duplicate joint')
        self.angles={k:0. for k in self.joints}
        for j in self.joints.values():
            axis=np.asarray(j['axis_local'],float)
            if axis.shape!=(3,) or not np.isfinite(axis).all() or not np.isclose(np.linalg.norm(axis),1): raise ValueError('axis')
            if scene.graph.transforms.parents.get(j['node'])!=j['parent']: raise ValueError('parent')
            m,_=scene.graph.get(j['node'],j['parent'])
            if not np.allclose(m,translation_matrix(j['pivot_parent_m'])): raise ValueError('initial pose')
    def step(self, key, value, dt):
        j=self.joints[key]
        if not j.get('control_enabled') or not math.isfinite(value) or not math.isfinite(dt) or dt<0: raise ValueError('command')
        if j['type']=='continuous': angle=self.angles[key]+value*6*dt
        elif j['type']=='revolute' and j['limits_deg'] and j['limits_deg'][0]<=value<=j['limits_deg'][1]: angle=value
        else: raise ValueError('joint limit')
        if not math.isfinite(angle): raise ValueError('overflow')
        self.scene.graph.update(frame_from=j['parent'],frame_to=j['node'],matrix=translation_matrix(j['pivot_parent_m'])@rotation_matrix(math.radians(angle%360),j['axis_local']))
        self.angles[key]=angle
        return angle
