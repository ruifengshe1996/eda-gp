import sys, glob, re, os
sys.path.insert(0, "/public_data/sheruifeng/research/eda_gp/scratch")
import frame_centroid as fc
for plot_dir in sys.argv[1:]:
    frames = sorted(glob.glob(os.path.join(plot_dir, "*iter*.png")))
    print(f"== {plot_dir}")
    print("iter | mean-dist(%h) | blue-px(%)")
    for f in frames:
        it = int(re.search(r"iter(\d+)", f).group(1))
        s = fc.frame_spread(f)
        if s:
            print(f"{it:5d} | {s[0]:6.2f} | {s[1]:5.2f}")
