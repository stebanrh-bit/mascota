"""Las mallas deben contener superficies utilizables y límites completos."""
import math
import struct

import pytest

from mascota.geometry import CurvedHornGeometry, FlameGeometry, TailGeometry, WingFrameGeometry, WingGeometry


@pytest.mark.parametrize('kind', [CurvedHornGeometry, TailGeometry, WingFrameGeometry, WingGeometry, FlameGeometry])
def test_mesh_has_finite_normals_and_bounds_that_contain_every_vertex(kind):
    mesh = kind()
    data = bytes(mesh.vertexData())
    assert len(data) > 1000
    assert len(data) % (3 * 24) == 0  # complete triangles
    minimum, maximum = mesh.boundsMin(), mesh.boundsMax()
    lower, upper = (minimum.x(), minimum.y(), minimum.z()), (maximum.x(), maximum.y(), maximum.z())
    assert all(hi > lo for lo, hi in zip(lower, upper))
    nonzero_normals = 0
    for vertex in struct.iter_unpack('6f', data):
        assert all(math.isfinite(value) for value in vertex)
        assert all(lo-.001 <= value <= hi+.001 for value,lo,hi in zip(vertex[:3],lower,upper))
        length = math.sqrt(sum(n*n for n in vertex[3:]))
        if length > .01:
            assert abs(length-1) < .001
            nonzero_normals += 1
    assert nonzero_normals / (len(data)/24) > .9
