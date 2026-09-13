import os
import glob
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

pred_dir = r"D:\Projects\border surv\models\ChangeFormer\samples_LEVIR\predict_CD_ChangeFormerV6"
label_dir = r"D:\Projects\border surv\models\ChangeFormer\samples_LEVIR\label"
a_dir = r"D:\Projects\border surv\models\ChangeFormer\samples_LEVIR\A"
b_dir = r"D:\Projects\border surv\models\ChangeFormer\samples_LEVIR\B"

pred_files = glob.glob(os.path.join(pred_dir, "*.png"))

def calc_metrics(pred, label):
    # Threshold at 128 (0-255)
    pred_bin = (pred > 128).astype(bool)
    label_bin = (label > 128).astype(bool)
    
    tp = np.sum(pred_bin & label_bin)
    fp = np.sum(pred_bin & ~label_bin)
    fn = np.sum(~pred_bin & label_bin)
    tn = np.sum(~pred_bin & ~label_bin)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
    return precision, recall, f1, iou, tp, fp, fn

num_samples = len(pred_files)
fig, axes = plt.subplots(num_samples, 4, figsize=(16, 4 * num_samples))
if num_samples == 1:
    axes = [axes]

overall_tp, overall_fp, overall_fn = 0, 0, 0

print(f"{'Sample':<25} | {'Precision':<9} | {'Recall':<9} | {'F1':<9} | {'IoU':<9}")
print("-" * 70)

for i, pred_path in enumerate(pred_files):
    filename = os.path.basename(pred_path)
    lbl_path = os.path.join(label_dir, filename)
    ap = os.path.join(a_dir, filename)
    bp = os.path.join(b_dir, filename)
    
    pred_img = np.array(Image.open(pred_path).convert('L'))
    lbl_img = np.array(Image.open(lbl_path).convert('L'))
    a_img = np.array(Image.open(ap).convert('RGB'))
    b_img = np.array(Image.open(bp).convert('RGB'))
    
    p, r, f1, iou, tp, fp, fn = calc_metrics(pred_img, lbl_img)
    overall_tp += tp
    overall_fp += fp
    overall_fn += fn
    
    print(f"{filename:<25} | {p:.4f}    | {r:.4f}    | {f1:.4f}    | {iou:.4f}")
    
    # Plotting
    ax = axes[i]
    ax[0].imshow(a_img)
    ax[0].set_title(f"T1: {filename}")
    ax[0].axis('off')
    
    ax[1].imshow(b_img)
    ax[1].set_title("T2")
    ax[1].axis('off')
    
    ax[2].imshow(lbl_img, cmap='gray')
    ax[2].set_title("Ground Truth")
    ax[2].axis('off')
    
    ax[3].imshow(pred_img, cmap='gray')
    ax[3].set_title(f"Pred (IoU: {iou:.3f})")
    ax[3].axis('off')

# Calculate overall
op = overall_tp / (overall_tp + overall_fp) if (overall_tp + overall_fp) > 0 else 0
or_ = overall_tp / (overall_tp + overall_fn) if (overall_tp + overall_fn) > 0 else 0
of1 = 2 * op * or_ / (op + or_) if (op + or_) > 0 else 0
oiou = overall_tp / (overall_tp + overall_fp + overall_fn) if (overall_tp + overall_fp + overall_fn) > 0 else 0

print("-" * 70)
print(f"{'OVERALL':<25} | {op:.4f}    | {or_:.4f}    | {of1:.4f}    | {oiou:.4f}")

plt.tight_layout()
contact_sheet_path = r"D:\Projects\border surv\models\ChangeFormer\samples_LEVIR\evaluation_contact_sheet.jpg"
plt.savefig(contact_sheet_path, dpi=150, bbox_inches='tight')
print(f"\nSaved contact sheet to: {contact_sheet_path}")
