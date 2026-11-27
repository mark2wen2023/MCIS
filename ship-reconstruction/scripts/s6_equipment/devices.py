"""Simplified parametric equipment, not hydrodynamic or as-built geometry."""
import numpy as np
import trimesh as t
from trimesh.transformations import rotation_matrix

def positive(*values):
    if not all(np.isfinite(v) and v>0 for v in values): raise ValueError('positive finite dimensions required')

def propeller(diameter, blade_count, hub_diameter, hub_length):
    positive(diameter,hub_diameter,hub_length)
    if not isinstance(blade_count,int) or not 2<=blade_count<=8 or hub_diameter>=diameter: raise ValueError('invalid propeller parameters')
    r=diameter/2; h=hub_diameter/2
    hub=t.creation.cylinder(radius=h,height=hub_length,transform=rotation_matrix(np.pi/2,[0,1,0]))
    # Radial blade envelope; no claimed pitch or foil section.
    parts=[hub]
    for i in range(blade_count):
        b=t.creation.box([hub_length*.2,(r-h)*.24,r-h]); b.apply_translation([0,0,(r+h)/2]); b.apply_transform(rotation_matrix(i*2*np.pi/blade_count,[1,0,0])); parts.append(b)
    return t.util.concatenate(parts)

def rudder(chord,span,thickness,axis_fraction):
    positive(chord,span,thickness)
    if not 0<=axis_fraction<=1 or thickness>=chord: raise ValueError('invalid rudder parameters')
    m=t.creation.box([chord,thickness,span]);m.apply_translation([(axis_fraction-.5)*chord,0,-span/2]);return m

def radar(length,width,height):
    positive(length,width,height);return t.creation.box([length,width,height])
