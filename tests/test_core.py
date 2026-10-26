"""Core numerical checks: matrix balancing and assignment conservation.

    pip install -e .[dev] && pytest
"""
import numpy as np
import pandas as pd

from railflow.assignment import assign_matrices
from railflow.distribution import furness


def test_furness_reproduces_margins():
    rng = np.random.default_rng(1)
    F = rng.random((40, 40)) + 0.01
    O = rng.random(40) * 100
    D = rng.permutation(O)
    A, B, _, err = furness(F, O, D, tol=1e-9, maxit=5000)
    T = A[:, None] * F * B[None, :]
    assert err < 1e-8
    np.testing.assert_allclose(T.sum(1), O, rtol=1e-6)
    np.testing.assert_allclose(T.sum(0), D, rtol=1e-6)


def _toy_network():
    # 0 - 1 - 2 - 3 in a line (1 km each), plus a slower bypass 1 - 4 - 2 (3 km)
    edges = pd.DataFrame({"u": [0, 1, 2, 1, 4], "v": [1, 2, 3, 4, 2],
                          "length_m": [1000.0, 1000.0, 1000.0, 1500.0, 1500.0]})
    edges["cost_m"] = edges.length_m
    nodes = np.zeros((5, 2))
    return edges, nodes


def test_assignment_uses_shortest_path_and_conserves_passenger_km():
    edges, nodes = _toy_network()
    snode = np.array([0, 3, 1])             # three stations at nodes 0, 3 and 1
    T = np.zeros((3, 3))
    T[0, 1] = 10.0                          # node 0 -> node 3
    T[2, 1] = 4.0                           # node 1 -> node 3
    flow = assign_matrices([T], edges, nodes, snode, verbose=False)[0]
    np.testing.assert_allclose(flow, [10.0, 14.0, 14.0, 0.0, 0.0])
    pkm = (flow * edges.length_m).sum()
    np.testing.assert_allclose(pkm, 10.0 * 3000 + 4.0 * 2000)


def test_assignment_of_several_matrices_is_additive():
    edges, nodes = _toy_network()
    snode = np.array([0, 3, 1])
    rng = np.random.default_rng(2)
    T1, T2 = rng.random((3, 3)), rng.random((3, 3))
    f = assign_matrices([T1, T2, T1 + T2], edges, nodes, snode, verbose=False)
    np.testing.assert_allclose(f[0] + f[1], f[2])
