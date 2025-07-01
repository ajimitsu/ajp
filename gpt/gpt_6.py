import torch
import numpy as np
from PIL import Image, ImageOps
from sklearn.preprocessing import LabelEncoder

def data_generator(X, y, batch_size):
    """
    A simple generator that yields shuffled mini-batches of data for PyTorch training.

    Args:
        X (np.ndarray): Feature matrix.
        y (np.ndarray): Target labels.
        batch_size (int): Size of each mini-batch.

    Yields:
        Tuple[torch.Tensor, torch.Tensor]: A mini-batch of features and labels as tensors.
    """
    indices = np.arange(len(X))
    np.random.shuffle(indices)
    for start in range(0, len(X), batch_size):
        end = start + batch_size
        batch_idx = indices[start:end]
        yield torch.tensor(X[batch_idx], dtype=torch.float32), torch.tensor(y[batch_idx], dtype=torch.long)


def keras_generator(X, y, batch_size):
    """
    A generator that yields random mini-batches of data indefinitely for Keras model training.

    Args:
        X (np.ndarray): Feature matrix.
        y (np.ndarray): Labels.
        batch_size (int): Number of samples per batch.

    Yields:
        Tuple[np.ndarray, np.ndarray]: A mini-batch of features and labels.
    """
    while True:
        indices = np.random.permutation(len(X))
        for start in range(0, len(X), batch_size):
            end = start + batch_size
            batch_ids = indices[start:end]
            yield X[batch_ids], y[batch_ids]


def augment_images(image_paths, batch_size):
    """
    Generator that loads and augments images in batches from disk on the fly.

    Args:
        image_paths (List[str]): List of file paths to images.
        batch_size (int): Number of images per batch.

    Yields:
        np.ndarray: A batch of augmented and normalized image arrays.
    """
    batch = []
    for path in image_paths:
        image = Image.open(path).resize((224, 224))
        image = ImageOps.mirror(image)  # Horizontal flip as augmentation
        batch.append(np.array(image) / 255.0)  # Normalize to [0, 1]
        if len(batch) == batch_size:
            yield np.array(batch)
            batch = []
    if batch:
        yield np.array(batch)


def preprocess_generator(X_texts, y_labels, tokenizer, batch_size=32):
    """
    Generator that performs on-the-fly tokenization and label encoding
    for training text models.

    Args:
        X_texts (List[str]): List of raw text samples.
        y_labels (List[str or int]): Class labels (can be strings or ints).
        tokenizer (Tokenizer): Keras tokenizer or compatible tokenizer.
        batch_size (int): Number of samples per batch.

    Yields:
        Tuple[List[List[int]], np.ndarray]: Tokenized text sequences and encoded labels.
    """
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y_labels)
    while True:
        indices = np.random.permutation(len(X_texts))
        for start in range(0, len(X_texts), batch_size):
            end = start + batch_size
            X_batch = tokenizer.texts_to_sequences([X_texts[i] for i in indices[start:end]])
            y_batch = y_encoded[indices[start:end]]
            yield X_batch, y_batch
