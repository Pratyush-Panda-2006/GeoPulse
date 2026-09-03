import torch
import sys

def verify():
    print(f"Python Version: {sys.version}")
    print(f"PyTorch Version: {torch.__version__}")
    
    cuda_available = torch.cuda.is_available()
    print(f"CUDA Available: {cuda_available}")
    
    if cuda_available:
        print(f"CUDA Device Count: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"Device {i}: {torch.cuda.get_device_name(i)}")
        print(f"Current Device: {torch.cuda.current_device()}")
    else:
        print("WARNING: CUDA is NOT available. Training will be extremely slow on CPU.")
        sys.exit(1)

if __name__ == "__main__":
    verify()
