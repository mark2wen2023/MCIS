# Chapter 10 supplement — Hydrostatic curves and local accuracy

Synthetic scan executed using hydrostatic_sensitivity.py at blob 6eec452140bb04b605a372d5846a25c0b6d271fd (verified). Stations [0,2,4] m, levels [0,1,2] m, all patches supported, half breadth A=z, B=1.2z. Waterline Z sampled at 0.25,0.5,0.75,1,1.25,1.5,1.75,2 m. The two model volume sequences are [0.25,1,2.25,4,6.25,9,12.25,16] and [0.3,1.2,2.7,4.8,7.5,10.8,14.7,19.2] m3 (rounded). Waterplane areas follow 8Z and 9.6Z m2. Across 14 adjacent model intervals, the largest absolute residual of volume increment minus trapezoidal waterplane area integral was 1.7763568394002505e-15 m3. This identity test is for the specified bilinear synthetic model, not a real hull or independent QA.

Remotion: animate the waterline, accumulate volume, plot area as the slope of the volume curve, highlight the integral over each interval. Then explain why matching aggregate volume cannot prove local shape accuracy. Do not publish real vessel numbers or geometry without permission.

QA source 282d618: research-chain and precision contract acceptance; five remaining world roundtrip and origin metadata assertions. Corrective commits 883210a and 157f022; regression tests 27de1b5; execution of these new tests pending. Research acceptance is not formal design approval or accident conclusion authorization.
