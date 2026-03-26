import numpy as np
import pandas as pd
import os

np.random.seed(42)

def generate_engagement_features(n_samples=10000):
    labels = np.random.choice([0, 1, 2, 3], size=n_samples, p=[0.15, 0.20, 0.40, 0.25])

    features = []
    for label in labels:
        base = label / 3.0
        aus = np.clip(np.random.normal(loc=base * 0.6, scale=0.15, size=17), 0, 1)
        head_pose = np.random.normal(loc=[base * 0.1, base * 0.1, 0], scale=[0.3, 0.3, 0.1])
        eye_gaze = np.clip(np.random.normal(loc=[base * 0.5]*4, scale=0.2, size=4), 0, 1)
        mouth_blink = np.random.normal(loc=[base * 0.3, 1 - base * 0.3], scale=0.1, size=2)
        temporal = np.random.normal(loc=base * 0.5, scale=0.2, size=24)
        feat = np.concatenate([aus, head_pose, eye_gaze, mouth_blink, temporal])
        features.append(feat)

    features = np.array(features)
    col_names = (
        [f'au_{i}' for i in range(17)] +
        ['head_pitch', 'head_yaw', 'head_roll'] +
        ['gaze_left_x', 'gaze_left_y', 'gaze_right_x', 'gaze_right_y'] +
        ['mouth_open', 'blink_rate'] +
        [f'temporal_{i}' for i in range(24)]
    )
    df = pd.DataFrame(features, columns=col_names)
    df['engagement_label'] = labels
    os.makedirs('ml_engine/data', exist_ok=True)
    df.to_csv('ml_engine/data/engagement_dataset.csv', index=False)
    print(f"Dataset generated: {n_samples} samples, shape: {df.shape}")
    print(f"Label distribution:")
    print(df['engagement_label'].value_counts().sort_index())
    return df

if __name__ == '__main__':
    generate_engagement_features(10000)