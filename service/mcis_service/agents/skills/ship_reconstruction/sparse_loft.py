"""Research-only sparse surface mesh with explicit supported cell mask."""
import math

def loft_sparse(stations, heights, widths, supported_cells):
    def finite(v):
        return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
    for axis in (stations,heights):
        if len(axis)<2 or not all(finite(v) for v in axis) or any(b<=a for a,b in zip(axis,axis[1:])):
            raise ValueError('invalid axis')
    n,m=len(stations),len(heights)
    if len(widths)!=n or any(len(row)!=m for row in widths):
        raise ValueError('invalid width grid')
    if len(supported_cells)!=n-1 or any(len(row)!=m-1 for row in supported_cells):
        raise ValueError('invalid support mask')
    if any(type(v) is not bool for row in supported_cells for v in row):
        raise ValueError('explicit boolean support required')
    if any(v is not None and (not finite(v) or v<0) for row in widths for v in row):
        raise ValueError('invalid half breadth')
    vertices,faces,skipped,face_cells=[],[],[],[]
    indices={}
    for i in range(n-1):
        for j in range(m-1):
            corners=[(i,j),(i,j+1),(i+1,j),(i+1,j+1)]
            if not supported_cells[i][j] or any(widths[a][b] is None for a,b in corners):
                skipped.append([i,j]);continue
            for a,b in corners:
                if (a,b) not in indices:
                    indices[a,b]=len(vertices)
                    vertices.append([stations[a],widths[a][b],heights[b]])
            a,b,c,d=[indices[p] for p in corners]
            faces.extend([[a,b,c],[b,d,c]])
            face_cells.extend([[i,j],[i,j]])
    return dict(vertices_m=vertices,triangles=faces,face_cells=face_cells,skipped_cells=skipped,research_only=True,lofting_authorized=False)
