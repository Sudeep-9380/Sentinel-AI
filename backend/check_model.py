from ultralytics import YOLO

model = YOLO("models/best.pt")

print("Model Classes:")
print(model.names)