import sys
import os
import argparse
import numpy as np
import torch
import torch.nn.functional as F
from multiprocessing.connection import Listener

from models.networks import define_G

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pipe_name', type=str, required=True, help="Named pipe for IPC")
    parser.add_argument('--project_name', default='CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw_train_test_200_linear_ce_multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256', type=str)
    parser.add_argument('--checkpoint_root', default=os.path.join(os.path.dirname(__file__), 'checkpoints'), type=str)
    parser.add_argument('--checkpoint_name', default='best_ckpt.pt', type=str)
    parser.add_argument('--checkpoint_dir', default=None, type=str, help='Direct path to checkpoint directory (overrides project_name resolution)')
    parser.add_argument('--gpu_ids', type=str, default='-1', help='gpu ids: e.g. 0. use -1 for CPU')
    parser.add_argument('--n_class', default=2, type=int)
    parser.add_argument('--embed_dim', default=256, type=int)
    parser.add_argument('--net_G', default='ChangeFormerV6', type=str)
    return parser.parse_args()

def _resolve_checkpoint(args):
    if args.checkpoint_dir:
        path = os.path.join(args.checkpoint_dir, args.checkpoint_name)
        if os.path.exists(path):
            return path
    path = os.path.join(args.checkpoint_root, args.project_name, args.checkpoint_name)
    if os.path.exists(path):
        return path
    path = os.path.join(args.checkpoint_root, 'ChangeFormerV6_LEVIR', args.checkpoint_name)
    if os.path.exists(path):
        return path
    for root, dirs, files in os.walk(args.checkpoint_root):
        if args.checkpoint_name in files:
            return os.path.join(root, args.checkpoint_name)
    raise FileNotFoundError(f"Checkpoint '{args.checkpoint_name}' not found.")

def preprocess_image(arr):
    # arr is [H, W, C] float32 in [0, 255]
    arr = arr / 255.0
    arr = (arr - 0.5) / 0.5
    arr = arr.transpose(2, 0, 1) # [C, H, W]
    return torch.from_numpy(arr).unsqueeze(0)

def main():
    args = get_args()
    device = torch.device("cpu")
    if args.gpu_ids != '-1' and torch.cuda.is_available():
        device = torch.device(f"cuda:{args.gpu_ids.split(',')[0]}")

    net_G = define_G(args=args, gpu_ids=args.gpu_ids.split(',') if args.gpu_ids != '-1' else [])
    checkpoint_path = _resolve_checkpoint(args)
    print(f"WORKER: Loading checkpoint from: {checkpoint_path}", flush=True)

    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    net_G.load_state_dict(checkpoint['model_G_state_dict'])
    net_G.to(device)
    net_G.eval()
    print("WORKER: Model loaded successfully.", flush=True)

    with Listener(args.pipe_name) as listener:
        while True:
            with listener.accept() as conn:
                msg = conn.recv()
                if msg == "STOP":
                    print("WORKER: Received STOP command. Exiting.", flush=True)
                    break
                if msg == "PING":
                    continue
                
                t1_np, t2_np = msg
                t1_tensor = preprocess_image(t1_np).to(device)
                t2_tensor = preprocess_image(t2_np).to(device)

                _, _, H, W = t1_tensor.shape
                tile_size = 256
                
                prob_map = torch.zeros((H, W), dtype=torch.float32, device=device)
                counts = torch.zeros((H, W), dtype=torch.float32, device=device)
                
                with torch.inference_mode():
                    for y in range(0, H, tile_size):
                        for x in range(0, W, tile_size):
                            y1 = y
                            y2 = min(y + tile_size, H)
                            x1 = x
                            x2 = min(x + tile_size, W)
                            
                            if y2 - y1 < tile_size and H >= tile_size:
                                y1 = max(0, H - tile_size)
                                y2 = H
                            if x2 - x1 < tile_size and W >= tile_size:
                                x1 = max(0, W - tile_size)
                                x2 = W
                            
                            t1_tile = t1_tensor[:, :, y1:y2, x1:x2]
                            t2_tile = t2_tensor[:, :, y1:y2, x1:x2]
                            
                            pad_y = max(0, tile_size - (y2 - y1))
                            pad_x = max(0, tile_size - (x2 - x1))
                            if pad_y > 0 or pad_x > 0:
                                t1_tile = F.pad(t1_tile, (0, pad_x, 0, pad_y))
                                t2_tile = F.pad(t2_tile, (0, pad_x, 0, pad_y))

                            outputs = net_G(t1_tile, t2_tile)
                            logits = outputs[-1]
                            
                            probs = F.softmax(logits, dim=1)[0, 1, :, :]
                            
                            if pad_y > 0 or pad_x > 0:
                                probs = probs[:y2-y1, :x2-x1]
                                
                            prob_map[y1:y2, x1:x2] += probs
                            counts[y1:y2, x1:x2] += 1
                            
                prob_map = prob_map / counts
                binary_mask = (prob_map > 0.5).float()
                
                prob_np = prob_map.cpu().numpy()
                mask_np = binary_mask.cpu().numpy().astype(np.uint8)
                
                conn.send((prob_np, mask_np))

if __name__ == "__main__":
    main()
