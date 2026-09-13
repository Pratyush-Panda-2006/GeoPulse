import os
import numpy as np
from PIL import Image

label_dir = r'd:\Projects\border surv\data\raw\LEVIR-CD\label'
files = os.listdir(label_dir)

changes = []
for f in files:
    path = os.path.join(label_dir, f)
    try:
        img = Image.open(path).convert('L')
        arr = np.array(img)
        changed_pixels = np.sum(arr > 127)
        pct = changed_pixels / (arr.shape[0]*arr.shape[1])
        changes.append((f, pct))
    except Exception:
        pass

changes.sort(key=lambda x: x[1], reverse=True)
print('Top 20 changes:')
for f, pct in changes[:20]:
    print(f'{f}: {pct:.4f}')
