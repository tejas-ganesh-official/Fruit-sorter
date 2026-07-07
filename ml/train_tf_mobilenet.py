import tensorflow as tf
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D, Dropout
from tensorflow.keras.callbacks import EarlyStopping

# ===========================
# Dataset Path
# ===========================
data_path = r"" # add path to dataset

IMG_SIZE = 224
BATCH_SIZE = 32

# ===========================
# Data Generator
# ===========================
datagen = ImageDataGenerator(
    rescale=1./255,
    rotation_range=25,
    zoom_range=0.2,
    horizontal_flip=True,
    validation_split=0.2
)

train_data = datagen.flow_from_directory(
    data_path,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="training"
)

val_data = datagen.flow_from_directory(
    data_path,
    target_size=(IMG_SIZE, IMG_SIZE),
    batch_size=BATCH_SIZE,
    class_mode="categorical",
    subset="validation"
)

num_classes = train_data.num_classes
print("Class mapping:", train_data.class_indices)

# ===========================
# Load Pretrained MobileNetV2
# ===========================
base_model = MobileNetV2(
    weights="imagenet",
    include_top=False,
    input_shape=(224, 224, 3)
)

# Freeze pretrained layers
for layer in base_model.layers:
    layer.trainable = False

# ===========================
# Custom Classification Head
# ===========================
model = Sequential([
    base_model,
    GlobalAveragePooling2D(),
    Dense(128, activation="relu"),
    Dropout(0.3),
    Dense(num_classes, activation="softmax")
])

model.compile(
    optimizer="adam",
    loss="categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()

# ===========================
# Early Stopping
# ===========================
early_stop = EarlyStopping(
    monitor="val_loss",
    patience=5,
    restore_best_weights=True
)

# ===========================
# Train
# ===========================
history = model.fit(
    train_data,
    validation_data=val_data,
    epochs=8,
    callbacks=[early_stop]
)

# ===========================
# Save Model
# ===========================
model.save("tomato_mobilenetV2.h5")
print("✅ Model saved as tomato_mobilenetV2.h5")
