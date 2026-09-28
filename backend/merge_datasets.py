from pathlib import Path
import shutil

BASE = Path("datasets")

DATASETS = {
    "fire": 0,
    "accident": 1,
    "fight": 2,
    "theft": 3,
}

DEST = BASE / "sentinel"

SPLITS = ["train", "valid", "test"]

# Create folders
for split in SPLITS:
    (DEST / split / "images").mkdir(parents=True, exist_ok=True)
    (DEST / split / "labels").mkdir(parents=True, exist_ok=True)

for dataset_name, class_id in DATASETS.items():
    print(f"Merging {dataset_name} -> class {class_id}")

    src_dataset = BASE / dataset_name

    for split in SPLITS:

        img_src = src_dataset / split / "images"
        lbl_src = src_dataset / split / "labels"

        if not img_src.exists():
            continue

        for img in img_src.iterdir():

            new_name = f"{dataset_name}_{img.name}"

            shutil.copy2(
                img,
                DEST / split / "images" / new_name
            )

            label = lbl_src / (img.stem + ".txt")

            new_label = DEST / split / "labels" / (Path(new_name).stem + ".txt")

            if label.exists():

                lines = []

                for line in label.read_text().splitlines():

                    if not line.strip():
                        continue

                    parts = line.split()

                    parts[0] = str(class_id)
                    print(f"{dataset_name}: {parts[0]}")

                    lines.append(" ".join(parts))

                new_label.write_text("\n".join(lines))

            else:
                new_label.write_text("")

print("Dataset merged successfully!")