"""
Normalization Parameters Generator for Raw Feature Pipeline

Generates params.json containing mean and standard deviation for the 6 raw sensor features.
Must be run after any changes to Dataset.csv to ensure normalization consistency.

Usage:
    python generate_params.py --dataset Dataset.csv --output ml_data/params.json

Output format (params.json):
    {
      "features": [
        {"name": "aX", "mean": 0.123, "std": 1.456},
        {"name": "aY", "mean": -0.045, "std": 1.234},
        {"name": "aZ", "mean": 9.801, "std": 1.789},
        {"name": "gX", "mean": 0.012, "std": 0.567},
        {"name": "gY", "mean": -0.008, "std": 0.432},
        {"name": "gZ", "mean": 0.003, "std": 0.321}
      ],
      "metadata": {
        "generated_from": "Dataset.csv",
        "n_samples": 50000,
        "generated_date": "2026-02-16T10:30:00Z"
      }
    }
"""

import argparse
import json
import os
import sys
from datetime import datetime

# Import feature extraction utility
try:
    from feature_utils import FEATURE_COLUMNS, load_training_data
except ImportError:
    # Try adding backend directory to path
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, backend_dir)
    from apps.ml.feature_utils import FEATURE_COLUMNS, load_training_data


def generate_normalization_params(dataset_path, output_path):
    """
    Calculate mean and standard deviation for each feature and save to params.json.

    Args:
        dataset_path (str): Path to Dataset.csv
        output_path (str): Path to save params.json

    Returns:
        dict: Generated parameters

    Raises:
        FileNotFoundError: If dataset doesn't exist
        ValueError: If dataset has invalid schema or zero std
    """
    print(f"Generating normalization parameters...")
    print(f"  Dataset: {dataset_path}")
    print(f"  Output: {output_path}")

    # Load training data using feature_utils
    X, y = load_training_data(dataset_path)

    print(f"\nCalculating statistics for {len(FEATURE_COLUMNS)} features...")

    # Calculate mean and std for each feature
    features = []
    for i, col_name in enumerate(FEATURE_COLUMNS):
        feature_data = X[:, i]

        mean_val = float(feature_data.mean())
        std_val = float(feature_data.std())

        # Validate std > 0 (prevent division by zero during normalization)
        if std_val <= 0:
            raise ValueError(
                f"Feature '{col_name}' has standard deviation of {std_val}. "
                f"Cannot normalize with zero variance. Check dataset for constant values."
            )

        features.append({
            "name": col_name,
            "mean": mean_val,
            "std": std_val
        })

        print(f"  {col_name}: mean={mean_val:.6f}, std={std_val:.6f}")

    # Build params object with metadata
    params = {
        "features": features,
        "metadata": {
            "generated_from": os.path.basename(dataset_path),
            "n_samples": len(X),
            "generated_date": datetime.utcnow().isoformat() + 'Z'
        }
    }

    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"\nCreated directory: {output_dir}")

    # Write to file with pretty formatting
    with open(output_path, 'w') as f:
        json.dump(params, f, indent=2)

    print(f"\n✓ Generated {output_path} with {len(features)} features")
    print(f"  Samples: {len(X)}")
    print(f"  Generated: {params['metadata']['generated_date']}")

    # Validate generated file can be loaded
    print("\nValidating generated params.json...")
    with open(output_path, 'r') as f:
        loaded = json.load(f)

    if len(loaded['features']) != 6:
        raise ValueError(f"Validation failed: expected 6 features, got {len(loaded['features'])}")

    print("✓ Validation successful")

    return params


def main():
    parser = argparse.ArgumentParser(
        description='Generate normalization parameters (params.json) for 6-feature ML pipeline'
    )
    parser.add_argument(
        '--dataset',
        type=str,
        default='Dataset.csv',
        help='Path to training dataset CSV file (default: Dataset.csv)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='ml_data/params.json',
        help='Path to save params.json (default: ml_data/params.json)'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify params.json exists and has correct schema'
    )

    args = parser.parse_args()

    # Verify mode: just check existing params.json
    if args.verify:
        print(f"Verifying {args.output}...")
        if not os.path.exists(args.output):
            print(f"✗ File not found: {args.output}")
            sys.exit(1)

        with open(args.output, 'r') as f:
            params = json.load(f)

        # Check schema
        if 'features' not in params:
            print("✗ Missing 'features' key")
            sys.exit(1)

        if len(params['features']) != 6:
            print(f"✗ Expected 6 features, got {len(params['features'])}")
            sys.exit(1)

        feature_names = [f['name'] for f in params['features']]
        if feature_names != FEATURE_COLUMNS:
            print(f"✗ Feature names mismatch")
            print(f"  Expected: {FEATURE_COLUMNS}")
            print(f"  Got: {feature_names}")
            sys.exit(1)

        print(f"✓ {args.output} is valid")
        print(f"  Features: {', '.join(feature_names)}")
        print(f"  Samples: {params['metadata'].get('n_samples', 'unknown')}")
        return

    # Generation mode
    try:
        params = generate_normalization_params(args.dataset, args.output)
        print("\n✓ Success: Normalization parameters generated")
        return params

    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
