"""
train_classifier.py
===================
Fine-tune MobileNetV2 on a real-world clothing dataset to improve
Wearlytics clothing classification accuracy.

Dataset used: Kaggle "Clothing Dataset (Full)" by Alexey Grigorev
  URL:   https://www.kaggle.com/datasets/agrigorev/clothing-dataset-full
  Size:  ~3.5 GB
  Type:  Real-world colour photos (phone shots, on person, on hangers)
  Licence: CC0 (Public Domain) — free for academic use

SETUP:
  1. Install Kaggle CLI:
       pip install kaggle
  2. Get your Kaggle API key from kaggle.com → Account → Create API Token
       Place the downloaded kaggle.json at ~/.kaggle/kaggle.json
  3. Download the dataset:
       kaggle datasets download agrigorev/clothing-dataset-full -p data/clothing --unzip
  4. Run this script:
       python train_classifier.py
  5. Trained model saved to:  app/services/clothing_model.pt

Expected training time: ~30–60 min on CPU (M-series Mac)
Expected accuracy on validation set: 75–87%

ALTERNATIVE (No Kaggle login):
  If you prefer not to use Kaggle, the script also works with any folder
  structure like:
      data/clothing/
          Tops/        ← put tops images here
          Bottoms/
          Shoes/
          Dresses/
          Outerwear/
          Accessories/
  Just set USE_CUSTOM_FOLDER = True below.
"""

import os
import json
import time
import random
import numpy as np
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, models, transforms
from torchvision.models import MobileNet_V2_Weights

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

DATA_DIR          = "data/organised"        # Root folder of organised dataset
MODEL_OUT         = "app/services/clothing_model.pt"
BATCH_SIZE        = 32
EPOCHS            = 15
LR_HEAD           = 1e-3    # Learning rate for the custom Dense head
LR_FINETUNE       = 1e-4    # Learning rate when unfreezing backbone
IMG_SIZE          = 224
VAL_SPLIT         = 0.15    # 15% validation
TEST_SPLIT        = 0.10    # 10% test
SEED              = 42
FREEZE_EPOCHS     = 7       # Train head only for first N epochs, then unfreeze top layers

# Set True if using a manually organised folder (see ALTERNATIVE above)
USE_CUSTOM_FOLDER = True

# ─────────────────────────────────────────────────────────────────────────────
# Kaggle dataset → Wearlytics category mapping
# Clothing Dataset (Full) has 20 classes; we map to 6 Wearlytics categories.
# ─────────────────────────────────────────────────────────────────────────────

CLASS_NAMES = ["Tops", "Bottoms", "Shoes", "Dresses", "Outerwear", "Accessories"]

# Kaggle folder name → Wearlytics category
KAGGLE_TO_WEARLYTICS = {
    # Tops
    "shirt":        "Tops",
    "t-shirt":      "Tops",
    "top":          "Tops",
    "blouse":       "Tops",
    "hoodie":       "Tops",
    "polo":         "Tops",
    "sweater":      "Tops",
    "sweatshirt":   "Tops",
    # Bottoms
    "pants":        "Bottoms",
    "jeans":        "Bottoms",
    "shorts":       "Bottoms",
    "skirt":        "Bottoms",
    "leggings":     "Bottoms",
    "trousers":     "Bottoms",
    # Shoes
    "shoes":        "Shoes",
    "boots":        "Shoes",
    "sandals":      "Shoes",
    "sneakers":     "Shoes",
    # Outerwear
    "jacket":       "Outerwear",
    "coat":         "Outerwear",
    "blazer":       "Outerwear",
    "outerwear":    "Outerwear",
    # Dresses
    "dress":        "Dresses",
    "gown":         "Dresses",
    # Accessories
    "hat":          "Accessories",
    "bag":          "Accessories",
    "belt":         "Accessories",
    "scarf":        "Accessories",
    "watch":        "Accessories",
    "sunglasses":   "Accessories",
    "accessories":  "Accessories",
    "tie":          "Accessories",
}


# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Reorganise the Kaggle dataset into CLASS_NAMES subfolders
# ─────────────────────────────────────────────────────────────────────────────

def reorganise_kaggle_data(raw_dir: str, out_dir: str = "data/organised") -> str:
    """
    The Kaggle dataset may have folders like 'Shirt', 'Jeans', etc.
    This maps them to Wearlytics 6 categories and copies images.
    """
    from shutil import copy2

    raw_dir  = Path(raw_dir)
    out_dir  = Path(out_dir)

    # Create target category folders
    for cat in CLASS_NAMES:
        (out_dir / cat).mkdir(parents=True, exist_ok=True)

    copied = 0
    skipped = 0
    for folder in raw_dir.iterdir():
        if not folder.is_dir():
            continue
        fname = folder.name.lower().strip()
        wearlytics_cat = KAGGLE_TO_WEARLYTICS.get(fname)
        if wearlytics_cat is None:
            # Try partial match
            for key, cat in KAGGLE_TO_WEARLYTICS.items():
                if key in fname or fname in key:
                    wearlytics_cat = cat
                    break
        if wearlytics_cat is None:
            print(f"  [SKIP] '{folder.name}' — no mapping found")
            skipped += 1
            continue
        for img_file in folder.glob("*"):
            if img_file.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
                dest = out_dir / wearlytics_cat / img_file.name
                if not dest.exists():
                    copy2(img_file, dest)
                    copied += 1

    print(f"\nOrganised dataset: {copied} images copied, {skipped} folders skipped.")
    print(f"Output: {out_dir}\n")
    return str(out_dir)


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Build data transforms + loaders
# ─────────────────────────────────────────────────────────────────────────────

def get_transforms():
    train_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE + 32, IMG_SIZE + 32)),
        transforms.RandomCrop(IMG_SIZE),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.3, contrast=0.2, saturation=0.2),
        transforms.RandomRotation(15),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])
    return train_tf, val_tf


def build_loaders(data_dir: str):
    train_tf, val_tf = get_transforms()

    # Full dataset with train transforms first (we'll override val/test later)
    full_dataset = datasets.ImageFolder(data_dir, transform=train_tf)

    total      = len(full_dataset)
    val_size   = int(total * VAL_SPLIT)
    test_size  = int(total * TEST_SPLIT)
    train_size = total - val_size - test_size

    generator = torch.Generator().manual_seed(SEED)
    train_ds, val_ds, test_ds = random_split(
        full_dataset, [train_size, val_size, test_size], generator=generator
    )

    # Apply val transforms to val/test subsets
    val_ds.dataset  = datasets.ImageFolder(data_dir, transform=val_tf)
    test_ds.dataset = datasets.ImageFolder(data_dir, transform=val_tf)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    print(f"Dataset split: {train_size} train | {val_size} val | {test_size} test")
    print(f"Classes: {full_dataset.classes}\n")

    return train_loader, val_loader, test_loader, full_dataset.classes


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Build MobileNetV2 model
# ─────────────────────────────────────────────────────────────────────────────

def build_model(num_classes: int) -> nn.Module:
    model = models.mobilenet_v2(weights=MobileNet_V2_Weights.IMAGENET1K_V1)

    # Freeze all backbone layers first
    for param in model.features.parameters():
        param.requires_grad = False

    # Replace classifier head
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(model.last_channel, 256),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(256, num_classes),
    )
    return model


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Training loop
# ─────────────────────────────────────────────────────────────────────────────

def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    correct    = 0
    total      = 0
    for inputs, labels in loader:
        inputs, labels = inputs.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss    = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * inputs.size(0)
        _, predicted = torch.max(outputs, 1)
        correct += (predicted == labels).sum().item()
        total   += labels.size(0)
    return total_loss / total, correct / total


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss = 0.0
    correct    = 0
    total      = 0
    all_preds  = []
    all_labels = []
    with torch.no_grad():
        for inputs, labels in loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            loss    = criterion(outputs, labels)
            total_loss += loss.item() * inputs.size(0)
            _, predicted = torch.max(outputs, 1)
            correct += (predicted == labels).sum().item()
            total   += labels.size(0)
            all_preds.extend(predicted.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
    return total_loss / total, correct / total, all_preds, all_labels


# ─────────────────────────────────────────────────────────────────────────────
# Step 5 — Evaluation metrics
# ─────────────────────────────────────────────────────────────────────────────

def compute_metrics(preds, labels, class_names):
    from collections import defaultdict
    n = len(class_names)

    # Confusion matrix
    cm = [[0] * n for _ in range(n)]
    for p, l in zip(preds, labels):
        cm[l][p] += 1

    # Per-class precision, recall, F1
    metrics = {}
    for i, cls in enumerate(class_names):
        tp = cm[i][i]
        fp = sum(cm[j][i] for j in range(n)) - tp
        fn = sum(cm[i][j] for j in range(n)) - tp
        precision = tp / (tp + fp + 1e-8)
        recall    = tp / (tp + fn + 1e-8)
        f1        = 2 * precision * recall / (precision + recall + 1e-8)
        metrics[cls] = {"precision": round(precision, 3),
                        "recall":    round(recall, 3),
                        "f1":        round(f1, 3),
                        "support":   tp + fn}

    return cm, metrics


def print_report(cm, metrics, class_names, accuracy):
    print("\n" + "=" * 65)
    print("EVALUATION REPORT")
    print("=" * 65)
    print(f"\nOverall Accuracy: {accuracy * 100:.2f}%\n")

    print(f"{'Class':<15} {'Precision':>10} {'Recall':>10} {'F1':>8} {'Support':>10}")
    print("-" * 58)
    for cls in class_names:
        m = metrics[cls]
        print(f"{cls:<15} {m['precision']:>10.3f} {m['recall']:>10.3f} {m['f1']:>8.3f} {m['support']:>10}")

    print("\nConfusion Matrix (rows=actual, cols=predicted):")
    header = f"{'':>12}" + "".join(f"{c[:8]:>10}" for c in class_names)
    print(header)
    for i, row in enumerate(cm):
        print(f"{class_names[i][:12]:>12}" + "".join(f"{v:>10}" for v in row))
    print("=" * 65)


# ─────────────────────────────────────────────────────────────────────────────
# Main training pipeline
# ─────────────────────────────────────────────────────────────────────────────

def main():
    torch.manual_seed(SEED)
    random.seed(SEED)
    np.random.seed(SEED)

    device = torch.device("mps" if torch.backends.mps.is_available()
                           else "cuda" if torch.cuda.is_available()
                           else "cpu")
    print(f"\nWearlytics MobileNetV2 Fine-Tuning")
    print(f"Device: {device}")
    print(f"Epochs: {EPOCHS}  Batch: {BATCH_SIZE}  Image: {IMG_SIZE}x{IMG_SIZE}\n")

    # ── Prepare data directory ──
    if USE_CUSTOM_FOLDER:
        organised_dir = DATA_DIR
    else:
        if not Path(DATA_DIR).exists():
            print(f"ERROR: {DATA_DIR} not found.")
            print("Please download the Kaggle dataset first:")
            print("  kaggle datasets download agrigorev/clothing-dataset-full -p data/clothing --unzip")
            return
        organised_dir = reorganise_kaggle_data(DATA_DIR, "data/organised")

    train_loader, val_loader, test_loader, dataset_classes = build_loaders(organised_dir)
    num_classes = len(dataset_classes)

    # ── Build model ──
    model = build_model(num_classes).to(device)
    criterion = nn.CrossEntropyLoss()

    # Phase 1: Train only the head (backbone frozen)
    optimizer = optim.Adam(model.classifier.parameters(), lr=LR_HEAD, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=FREEZE_EPOCHS)

    best_val_acc = 0.0
    history = []

    print(f"Phase 1: Training classifier head ({FREEZE_EPOCHS} epochs, backbone frozen)")
    print("-" * 55)

    for epoch in range(1, FREEZE_EPOCHS + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        vl_loss, vl_acc, _, _ = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        history.append({"epoch": epoch, "tr_loss": round(tr_loss, 4),
                         "tr_acc": round(tr_acc, 4), "val_acc": round(vl_acc, 4)})
        print(f"  Ep {epoch:02d}/{EPOCHS}  TrainAcc={tr_acc*100:.1f}%  ValAcc={vl_acc*100:.1f}%  [{elapsed:.0f}s]")

        if vl_acc > best_val_acc:
            best_val_acc = vl_acc
            torch.save(model.state_dict(), MODEL_OUT)
            print(f"            ✓ Model saved (val_acc={vl_acc*100:.1f}%)")

    # Phase 2: Unfreeze top layers and fine-tune with lower LR
    print(f"\nPhase 2: Fine-tuning top MobileNetV2 layers ({EPOCHS - FREEZE_EPOCHS} epochs)")
    print("-" * 55)

    # Unfreeze last 3 feature blocks
    for i, layer in enumerate(model.features):
        if i >= len(model.features) - 3:
            for param in layer.parameters():
                param.requires_grad = True

    optimizer = optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=LR_FINETUNE, weight_decay=1e-4
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=EPOCHS - FREEZE_EPOCHS
    )

    for epoch in range(FREEZE_EPOCHS + 1, EPOCHS + 1):
        t0 = time.time()
        tr_loss, tr_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        vl_loss, vl_acc, _, _ = evaluate(model, val_loader, criterion, device)
        scheduler.step()
        elapsed = time.time() - t0

        history.append({"epoch": epoch, "tr_loss": round(tr_loss, 4),
                         "tr_acc": round(tr_acc, 4), "val_acc": round(vl_acc, 4)})
        print(f"  Ep {epoch:02d}/{EPOCHS}  TrainAcc={tr_acc*100:.1f}%  ValAcc={vl_acc*100:.1f}%  [{elapsed:.0f}s]")

        if vl_acc > best_val_acc:
            best_val_acc = vl_acc
            torch.save(model.state_dict(), MODEL_OUT)
            print(f"            ✓ Model saved (val_acc={vl_acc*100:.1f}%)")

    # ── Final test evaluation ──
    print(f"\nLoading best model for test evaluation...")
    model.load_state_dict(torch.load(MODEL_OUT, map_location=device))
    _, test_acc, test_preds, test_labels = evaluate(model, test_loader, criterion, device)

    cm, metrics = compute_metrics(test_preds, test_labels, dataset_classes)
    print_report(cm, metrics, dataset_classes, test_acc)

    # ── Save training history and metrics ──
    results = {
        "best_val_accuracy":  round(best_val_acc, 4),
        "test_accuracy":      round(test_acc, 4),
        "epochs_trained":     EPOCHS,
        "class_names":        dataset_classes,
        "per_class_metrics":  metrics,
        "history":            history,
    }
    results_path = "app/services/model_evaluation.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Model saved to: {MODEL_OUT}")
    print(f"✓ Evaluation results saved to: {results_path}")
    print(f"\nBest validation accuracy: {best_val_acc*100:.2f}%")
    print(f"Final test accuracy:       {test_acc*100:.2f}%")
    print("\nThe Flask app will automatically use the fine-tuned model")
    print("(clothing_model.pt) on next restart.")


if __name__ == "__main__":
    main()
