from pathlib import Path
import os

# Path to your fight dataset
dataset_path = Path("datasets/fight")

splits = ["train", "valid", "test"]

kept = 0
removed = 0
deleted_files = 0

for split in splits:
    labels_dir = dataset_path / split / "labels"
    images_dir = dataset_path / split / "images"

    if not labels_dir.exists():
        continue

    for label_file in labels_dir.glob("*.txt"):

        new_lines = []

        with open(label_file, "r") as f:
            lines = f.readlines()

        for line in lines:
            parts = line.strip().split()

            if not parts:
                continue

            cls = int(parts[0])

            # Keep only "fight" (original class id = 1)
            if cls == 1:
                parts[0] = "0"   # Rename fight -> class 0
                new_lines.append(" ".join(parts))

        if new_lines:
            with open(label_file, "w") as f:
                f.write("\n".join(new_lines) + "\n")
            kept += 1

        else:
            # Remove empty label
            os.remove(label_file)
            deleted_files += 1

            stem = label_file.stem

            # Delete corresponding image
            for ext in [".jpg", ".jpeg", ".png"]:
                img = images_dir / (stem + ext)
                if img.exists():
                    img.unlink()
                    break

            removed += 1

print("\nFinished!")
print(f"Files kept     : {kept}")
print(f"Files removed  : {removed}")
print(f"Labels deleted : {deleted_files}")