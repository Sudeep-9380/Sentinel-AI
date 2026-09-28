import cv2

print("Opening laptop webcam...")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Could not open laptop webcam.")
    print("Check whether another application is using the camera.")
    exit()

print("✅ Laptop webcam opened successfully.")
print("Press Q to close.")

while True:
    success, frame = cap.read()

    if not success:
        print("❌ Failed to read webcam frame.")
        break

    cv2.imshow("Sentinel - Laptop Camera", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

print("Webcam test finished.")