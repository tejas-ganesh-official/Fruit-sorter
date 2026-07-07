"""
Train the fruit classifier (PyTorch, EfficientNetV2-S).

This produces the exact checkpoint that inference.py loads:
    checkpoint = {"model_state_dict": ..., "classes": [...]}

Dataset layout (ImageFolder) — one sub-folder per class:

    dataset/
        damaged/   img1.jpg img2.jpg ...
        old/       ...
        ripe/      ...
        unripe/    ...

Usage:
    python train.py --data ./dataset --epochs 15 --out fruit_efficientnetv2s.pth
"""

import argparse
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, models, transforms

# Keep this order identical to `classes` in inference.py
CLASSES = ["damaged", "old", "ripe", "unripe"]
IMG_SIZE = 224

# ImageNet normalization — must match inference.py
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def build_loaders(data_dir, batch_size, val_split):
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(0.2, 0.2, 0.2),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    eval_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])

    full = datasets.ImageFolder(data_dir)
    # Sanity-check the folders match what inference.py expects
    found = sorted(full.classes)
    if found != sorted(CLASSES):
        raise ValueError(
            f"Dataset classes {found} != expected {sorted(CLASSES)}. "
            "Rename your folders to: " + ", ".join(CLASSES)
        )

    n_val = int(len(full) * val_split)
    n_train = len(full) - n_val
    train_ds, val_ds = random_split(
        full, [n_train, n_val],
        generator=torch.Generator().manual_seed(42),
    )
    train_ds.dataset.transform = train_tf
    val_ds.dataset.transform = eval_tf

    return (
        DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=2),
        DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=2),
        full.class_to_idx,
    )


def build_model(freeze_backbone=True):
    model = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.IMAGENET1K_V1)
    if freeze_backbone:
        for p in model.parameters():
            p.requires_grad = False
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, len(CLASSES))
    return model


def run_epoch(model, loader, criterion, device, optimizer=None):
    train = optimizer is not None
    model.train() if train else model.eval()
    total, correct, loss_sum = 0, 0, 0.0
    with torch.set_grad_enabled(train):
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            out = model(x)
            loss = criterion(out, y)
            if train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            loss_sum += loss.item() * x.size(0)
            correct += (out.argmax(1) == y).sum().item()
            total += x.size(0)
    return loss_sum / total, correct / total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="path to dataset root (ImageFolder)")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--val-split", type=float, default=0.2)
    ap.add_argument("--out", default="fruit_efficientnetv2s.pth")
    ap.add_argument("--unfreeze", action="store_true",
                    help="fine-tune the whole backbone (slower, needs more data)")
    args = ap.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device:", device)

    train_loader, val_loader, class_to_idx = build_loaders(
        args.data, args.batch, args.val_split
    )
    print("Class mapping:", class_to_idx)

    model = build_model(freeze_backbone=not args.unfreeze).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()), lr=args.lr
    )

    best_acc = 0.0
    for epoch in range(1, args.epochs + 1):
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, device, optimizer)
        val_loss, val_acc = run_epoch(model, val_loader, criterion, device)
        print(f"Epoch {epoch:02d}/{args.epochs}  "
              f"train_loss={tr_loss:.3f} acc={tr_acc:.3f}  "
              f"val_loss={val_loss:.3f} acc={val_acc:.3f}")

        if val_acc >= best_acc:
            best_acc = val_acc
            torch.save(
                {"model_state_dict": model.state_dict(), "classes": CLASSES},
                args.out,
            )
            print(f"  saved -> {args.out} (val_acc={val_acc:.3f})")

    print(f"Done. Best val_acc={best_acc:.3f}. Checkpoint: {args.out}")


if __name__ == "__main__":
    main()
