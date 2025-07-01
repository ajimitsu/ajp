import os
import numpy as np
from PIL import Image
from tensorflow.keras.utils import Sequence

class CustomImageGenerator(Sequence):
    """
    A custom image data generator that loads, preprocesses, and batches images on the fly.
    🔍 Why Use a Custom Generator?
    You need non-image inputs (e.g., masks, coordinates).

    You want custom augmentations or label formats.

    You want to balance or resample the dataset manually.
    """
    def __init__(self, image_dir, batch_size=32, image_size=(150, 150), shuffle=True):
        self.image_dir = image_dir
        self.batch_size = batch_size
        self.image_size = image_size
        self.shuffle = shuffle
        self.classes = sorted(os.listdir(image_dir))
        self.filepaths, self.labels = self._load_dataset()
        self.on_epoch_end()

    def _load_dataset(self):
        filepaths, labels = [], []
        for label_index, class_name in enumerate(self.classes):
            class_dir = os.path.join(self.image_dir, class_name)
            for fname in os.listdir(class_dir):
                filepaths.append(os.path.join(class_dir, fname))
                labels.append(label_index)
        return np.array(filepaths), np.array(labels)

    def __len__(self):
        return int(np.ceil(len(self.filepaths) / self.batch_size))

    def __getitem__(self, idx):
        batch_paths = self.filepaths[idx * self.batch_size:(idx + 1) * self.batch_size]
        batch_labels = self.labels[idx * self.batch_size:(idx + 1) * self.batch_size]

        images = []
        for path in batch_paths:
            img = Image.open(path).resize(self.image_size).convert("RGB")
            img = np.array(img) / 255.0
            images.append(img)

        return np.array(images), np.array(batch_labels)

    def on_epoch_end(self):
        if self.shuffle:
            indices = np.random.permutation(len(self.filepaths))
            self.filepaths, self.labels = self.filepaths[indices], self.labels[indices]

# Instantiate and use
train_gen = CustomImageGenerator('dataset/train')
val_gen = CustomImageGenerator('dataset/val', shuffle=False)

# Model remains the same
model.fit(train_gen, validation_data=val_gen, epochs=10)
