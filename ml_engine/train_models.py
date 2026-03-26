import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score
import tensorflow as tf
from tensorflow.keras import layers, models, callbacks
import joblib
import os
import json

os.makedirs('ml_engine/saved_models', exist_ok=True)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

print("Loading dataset...")
df = pd.read_csv('ml_engine/data/engagement_dataset.csv')
X = df.drop('engagement_label', axis=1).values
y = df['engagement_label'].values

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)
joblib.dump(scaler, 'ml_engine/saved_models/scaler.pkl')
print("Scaler saved.")

X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y, test_size=0.2, random_state=42, stratify=y
)

X_train_cnn = X_train.reshape(X_train.shape[0], X_train.shape[1], 1)
X_test_cnn  = X_test.reshape(X_test.shape[0], X_test.shape[1], 1)
y_train_cat = tf.keras.utils.to_categorical(y_train, 4)
y_test_cat  = tf.keras.utils.to_categorical(y_test, 4)

INPUT_SHAPE = (X_train_cnn.shape[1], 1)


def build_1d_cnn(input_shape=INPUT_SHAPE, num_classes=4):
    model = models.Sequential([
        layers.Input(shape=input_shape),
        layers.Conv1D(64, 3, activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling1D(2),
        layers.Dropout(0.25),
        layers.Conv1D(128, 3, activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.MaxPooling1D(2),
        layers.Dropout(0.25),
        layers.Conv1D(256, 3, activation='relu', padding='same'),
        layers.BatchNormalization(),
        layers.GlobalAveragePooling1D(),
        layers.Dense(128, activation='relu'),
        layers.Dropout(0.5),
        layers.Dense(64, activation='relu'),
        layers.Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model


def residual_block(x, filters, kernel_size=3):
    shortcut = x
    x = layers.Conv1D(filters, kernel_size, padding='same', activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Conv1D(filters, kernel_size, padding='same')(x)
    x = layers.BatchNormalization()(x)
    if shortcut.shape[-1] != filters:
        shortcut = layers.Conv1D(filters, 1, padding='same')(shortcut)
    x = layers.Add()([x, shortcut])
    x = layers.Activation('relu')(x)
    return x


def build_1d_resnet(input_shape=INPUT_SHAPE, num_classes=4):
    inputs = layers.Input(shape=input_shape)
    x = layers.Conv1D(64, 7, padding='same', activation='relu')(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.MaxPooling1D(2)(x)
    x = residual_block(x, 64)
    x = residual_block(x, 128)
    x = layers.MaxPooling1D(2)(x)
    x = residual_block(x, 256)
    x = layers.GlobalAveragePooling1D()(x)
    x = layers.Dense(128, activation='relu')(x)
    x = layers.Dropout(0.5)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    model = models.Model(inputs, outputs)
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model


def train_single(model, name, epochs=30):
    print(f"\nTraining {name}...")
    cb = [
        callbacks.EarlyStopping(patience=5, restore_best_weights=True, verbose=0),
        callbacks.ReduceLROnPlateau(patience=3, factor=0.5, verbose=0)
    ]
    model.fit(X_train_cnn, y_train_cat, epochs=epochs, batch_size=64,
              validation_split=0.15, callbacks=cb, verbose=1)
    loss, acc = model.evaluate(X_test_cnn, y_test_cat, verbose=0)
    print(f"{name} Accuracy: {acc*100:.2f}%")
    model.save(f'ml_engine/saved_models/{name}.keras')
    print(f"Saved: ml_engine/saved_models/{name}.keras")
    return model, acc


def train_bagging(build_fn, name, n_estimators=5):
    print(f"\nTraining Bagging Ensemble: {name} ({n_estimators} models)...")
    ensemble = []
    n_train = len(X_train_cnn)
    for i in range(n_estimators):
        print(f"  Estimator {i+1}/{n_estimators}...")
        idx = np.random.choice(n_train, n_train, replace=True)
        m = build_fn()
        cb = [callbacks.EarlyStopping(patience=4, restore_best_weights=True, verbose=0)]
        m.fit(X_train_cnn[idx], y_train_cat[idx], epochs=25, batch_size=64,
              validation_split=0.1, callbacks=cb, verbose=0)
        m.save(f'ml_engine/saved_models/{name}_estimator_{i}.keras')
        ensemble.append(m)
        print(f"  Saved estimator {i+1}")
    preds = np.mean([m.predict(X_test_cnn, verbose=0) for m in ensemble], axis=0)
    acc = accuracy_score(y_test, np.argmax(preds, axis=1))
    print(f"{name} Ensemble Accuracy: {acc*100:.2f}%")
    return ensemble, acc


if __name__ == '__main__':
    print("="*50)
    print("STARTING MODEL TRAINING")
    print("="*50)

    cnn_model,    cnn_acc    = train_single(build_1d_cnn(),    '1d_cnn')
    resnet_model, resnet_acc = train_single(build_1d_resnet(), '1d_resnet')

    cnn_bag,    cnn_bag_acc    = train_bagging(build_1d_cnn,    'cnn_bagging',    n_estimators=5)
    resnet_bag, resnet_bag_acc = train_bagging(build_1d_resnet, 'resnet_bagging', n_estimators=5)

    # Hybrid ensemble accuracy
    all_models = cnn_bag + resnet_bag
    preds = np.mean([m.predict(X_test_cnn, verbose=0) for m in all_models], axis=0)
    hybrid_acc = accuracy_score(y_test, np.argmax(preds, axis=1))

    results = {
        'cnn_individual':    round(cnn_acc * 100, 2),
        'resnet_individual': round(resnet_acc * 100, 2),
        'cnn_bagging':       round(cnn_bag_acc * 100, 2),
        'resnet_bagging':    round(resnet_bag_acc * 100, 2),
        'hybrid_ensemble':   round(hybrid_acc * 100, 2),
    }
    with open('ml_engine/saved_models/accuracy_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*50)
    print("FINAL RESULTS:")
    for k, v in results.items():
        print(f"  {k:25s}: {v}%")
    print("="*50)
    print("\nAll models saved to ml_engine/saved_models/")