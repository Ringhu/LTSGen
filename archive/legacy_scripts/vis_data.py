import json
import random
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.font_manager as fm
import os
import numpy as np

# 1. Read Data from File
filename = '/cluster/home/user1/hulining/TSDataset/LTSGen/gen_tst_dataset/ucr_test_merged.jsonl'
lines = []
with open(filename, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Pick a random sample
random_line = random.choice(lines)
data = json.loads(random_line)

# Extract relevant fields
# Timeseries is usually [[val], [val], ...], flatten it
timeseries_raw = data.get('timeseries', [])
timeseries = [x[0] if isinstance(x, list) else x for x in timeseries_raw]
indices = range(len(timeseries))

# Captions
dense_caps = data.get('dense_captions', {})
global_caption = dense_caps.get('global', {}).get('zh', "No global caption found.")
local_captions = dense_caps.get('local', [])
series_key = data.get('series_key', 'Unknown Series')

# 2. Find CJK Font
font_path = None
candidates = [
    '/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc',   # ✅ 加这一条
    '/usr/share/fonts/google-noto-cjk/NotoSansCJK-Medium.ttc',
    '/usr/share/fonts/google-noto-cjk/NotoSansCJK-Bold.ttc',

    '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
    '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
    '/usr/share/fonts/truetype/arphic/uming.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
    '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf'
]

for p in candidates:
    if os.path.exists(p):
        font_path = p
        break

if font_path:
    prop = fm.FontProperties(fname=font_path)
    print(f"Using font: {font_path}")
else:
    prop = fm.FontProperties()
    print("Warning: CJK font not explicitly found.")

# 3. Setup Plot
fig = plt.figure(figsize=(16, 12))
gs = gridspec.GridSpec(2, 1, height_ratios=[2, 1.2])

# -- Top Subplot: Time Series --
ax = plt.subplot(gs[0])
ax.plot(indices, timeseries, label='Series Value', color='navy', linewidth=1.5)

# Plot local captions
# Use a colormap
colors = plt.cm.tab20(np.linspace(0, 1, len(local_captions)))
caption_texts = [] 

for i, cap in enumerate(local_captions):
    start = cap.get('start')
    end = cap.get('end')
    # Use 'description_zh' or fallback to english or generic
    desc = cap.get('description_zh', cap.get('description_en', 'No description'))
    cap_type = cap.get('type', 'unknown')
    
    # Assign an ID
    cid = i + 1
    caption_texts.append(f"[{cid}] {desc}")
    
    # Visual marking
    color = colors[i]
    
    if start is not None and end is not None:
        if start == end: # Point event
            ax.axvline(x=start, color=color, linestyle='--', alpha=0.7)
            ax.scatter([start], [timeseries[start]], color=color, s=50, zorder=5)
            # Annotation arrow
            ax.annotate(f"[{cid}]", xy=(start, timeseries[start]), xytext=(start, timeseries[start] + (max(timeseries)-min(timeseries))*0.05),
                        arrowprops=dict(facecolor=color, arrowstyle="->"),
                        fontproperties=prop, fontsize=10, color=color, fontweight='bold')
        else: # Interval
            mid_idx = (start + end) // 2
            # Alternate label position top/bottom
            y_pos = max(timeseries) if i % 2 == 0 else min(timeseries)
            
            ax.axvspan(start, end, color=color, alpha=0.1)
            ax.text(mid_idx, y_pos, 
                    f"[{cid}]", color=color, ha='center', fontweight='bold', fontsize=10)

ax.set_title(f"Time Series Visualization: {series_key}", fontsize=14)
ax.set_xlabel("Time Index")
ax.set_ylabel("Value")
ax.grid(True, linestyle=':', alpha=0.6)

# -- Bottom Subplot: Captions Text --
ax_text = plt.subplot(gs[1])
ax_text.axis('off')

def wrap_text(text, width=90):
    lines = []
    for i in range(0, len(text), width):
        lines.append(text[i:i+width])
    return '\n'.join(lines)

text_content = "Global Caption (全局描述):\n"
text_content += wrap_text(global_caption, 95) + "\n\n"
text_content += "Local Captions (局部描述):\n"

for ct in caption_texts:
    text_content += wrap_text(ct, 95) + "\n"

ax_text.text(0.01, 0.95, text_content, transform=ax_text.transAxes, 
             fontsize=11, fontproperties=prop, verticalalignment='top', linespacing=1.4)

plt.tight_layout()
plt.savefig('random_sample_vis.png')
print(f"Visualized sample: {series_key}")