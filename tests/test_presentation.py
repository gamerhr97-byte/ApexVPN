import pytest
from nextapp.presentation import latency_color

@pytest.mark.parametrize('ping,color',[(0,'#22C55E'),(149.99,'#22C55E'),(150,'#4F8CFF'),(199.99,'#4F8CFF'),(200,'#EF4444'),(900,'#EF4444')])
def test_requested_latency_boundaries(ping,color):assert latency_color(ping)==color
