#!/usr/bin/env python
"""
Master Pipeline Script - Run All Data Preparation Stages

Orchestrates the complete ML/DL data preparation pipeline by running all three stages:
1. Dataset Preprocessing (User Story 1)
2. Feature Engineering (User Story 2)
3. Sequence Preparation (User Story 3)

Usage:
    python run_all.py [--input PATH] [--output DIR] [--skip-stage STAGE]

Arguments:
    --input PATH        Path to Dataset.csv (default: ../../../Dataset.csv)
    --output DIR        Output directory (default: ../processed/)
    --skip-stage STAGE  Skip a stage (1, 2, or 3) - useful if already completed

Example:
    # Run full pipeline
    python run_all.py

    # Run with custom paths
    python run_all.py --input /path/to/Dataset.csv --output /path/to/output/

    # Skip stage 2 if already done
    python run_all.py --skip-stage 2
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))

# Import stage scripts as modules
try:
    import importlib.util

    # Stage 1: Preprocessing
    preprocess_spec = importlib.util.spec_from_file_location(
        "preprocess",
        Path(__file__).parent / "1_preprocess.py"
    )
    preprocess_module = importlib.util.module_from_spec(preprocess_spec)

    # Stage 2: Feature Engineering
    feature_spec = importlib.util.spec_from_file_location(
        "feature_engineering",
        Path(__file__).parent / "2_feature_engineering.py"
    )
    feature_module = importlib.util.module_from_spec(feature_spec)

    # Stage 3: Sequence Preparation
    sequence_spec = importlib.util.spec_from_file_location(
        "sequence_preparation",
        Path(__file__).parent / "3_sequence_preparation.py"
    )
    sequence_module = importlib.util.module_from_spec(sequence_spec)

except Exception as e:
    print(f"[ERROR] Failed to load stage modules: {e}")
    sys.exit(1)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run complete ML/DL data preparation pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--input",
        type=str,
        default="../../../Dataset.csv",
        help="Path to Dataset.csv (default: ../../../Dataset.csv)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="../processed/",
        help="Output directory (default: ../processed/)"
    )
    parser.add_argument(
        "--skip-stage",
        type=int,
        choices=[1, 2, 3],
        help="Skip a specific stage (1=preprocess, 2=features, 3=sequences)"
    )
    parser.add_argument(
        "--random-state",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)"
    )
    return parser.parse_args()


def print_header():
    """Print pipeline header."""
    print("=" * 80)
    print("ML/DL DATA PREPARATION PIPELINE - MASTER ORCHESTRATOR")
    print("=" * 80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("This script will execute all three data preparation stages:")
    print("  Stage 1: Dataset Preprocessing (User Story 1)")
    print("  Stage 2: Feature Engineering (User Story 2)")
    print("  Stage 3: Sequence Preparation (User Story 3)")
    print("=" * 80)


def run_stage(stage_num: int, stage_name: str, run_function, args_dict: dict):
    """
    Run a single pipeline stage with error handling.

    Parameters:
    -----------
    stage_num : int
        Stage number (1, 2, or 3)
    stage_name : str
        Human-readable stage name
    run_function : callable
        Function to execute for this stage
    args_dict : dict
        Arguments to pass to the stage

    Returns:
    --------
    elapsed_time : float
        Time taken to run stage in seconds
    success : bool
        Whether stage completed successfully
    """
    print(f"\n{'=' * 80}")
    print(f"STAGE {stage_num}: {stage_name}")
    print(f"{'=' * 80}")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")

    stage_start = time.time()

    try:
        # Run stage
        run_function(**args_dict)

        elapsed = time.time() - stage_start
        print(f"\nStage {stage_num} completed in {elapsed:.2f} seconds [OK]")
        return elapsed, True

    except Exception as e:
        elapsed = time.time() - stage_start
        print(f"\n[ERROR] Stage {stage_num} failed after {elapsed:.2f} seconds:")
        print(f"  {str(e)}")
        import traceback
        traceback.print_exc()
        return elapsed, False


def get_output_summary(output_dir: str):
    """
    Generate summary of output files.

    Parameters:
    -----------
    output_dir : str
        Output directory path

    Returns:
    --------
    summary : list
        List of (filename, size_str, description) tuples
    """
    output_files = [
        ("train_normalized.npy", "Preprocessed train features (normalized)"),
        ("test_normalized.npy", "Preprocessed test features (normalized)"),
        ("train_labels.npy", "Preprocessed train labels"),
        ("test_labels.npy", "Preprocessed test labels"),
        ("normalization_params.json", "Normalization parameters (mean/std per axis)"),
        ("preprocessing_report.txt", "Preprocessing summary report"),
        ("train_features.csv", "ML feature matrix (train set)"),
        ("test_features.csv", "ML feature matrix (test set)"),
        ("train_sequences.npy", "DL sequence tensor (train set)"),
        ("test_sequences.npy", "DL sequence tensor (test set)"),
        ("train_seq_labels.npy", "DL sequence labels (train set)"),
        ("test_seq_labels.npy", "DL sequence labels (test set)"),
    ]

    summary = []
    total_size = 0

    for filename, description in output_files:
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            size_bytes = os.path.getsize(filepath)
            total_size += size_bytes

            if size_bytes < 1024:
                size_str = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                size_str = f"{size_bytes / (1024 * 1024):.2f} MB"

            summary.append((filename, size_str, description))

    return summary, total_size


def print_final_report(stages_run: list, stage_times: dict, output_dir: str, total_time: float):
    """
    Print final pipeline summary report.

    Parameters:
    -----------
    stages_run : list
        List of (stage_num, stage_name, success) tuples
    stage_times : dict
        Dictionary mapping stage_num to elapsed time
    output_dir : str
        Output directory path
    total_time : float
        Total pipeline execution time
    """
    print("\n" + "=" * 80)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total time: {total_time:.2f} seconds ({total_time / 60:.2f} minutes)")
    print()

    # Stage timing breakdown
    print("Stage Timing:")
    for stage_num, stage_name, success in stages_run:
        elapsed = stage_times.get(stage_num, 0)
        status = "[OK]" if success else "[FAILED]"
        percent = (elapsed / total_time * 100) if total_time > 0 else 0
        print(f"  Stage {stage_num} ({stage_name}): {elapsed:.2f}s ({percent:.1f}%) {status}")

    print()

    # Output file summary
    print("Output Files:")
    file_summary, total_size = get_output_summary(output_dir)

    if file_summary:
        for filename, size_str, description in file_summary:
            print(f"  - {filename:30s} {size_str:>10s}  {description}")

        total_size_mb = total_size / (1024 * 1024)
        print(f"\n  Total output size: {total_size_mb:.2f} MB")
    else:
        print("  No output files found (pipeline may have failed)")

    print()
    print("Output directory: " + os.path.abspath(output_dir))
    print("=" * 80)


def main():
    """Main orchestration function."""
    # Print header
    print_header()

    # Parse arguments
    args = parse_arguments()
    input_path = args.input
    output_dir = args.output
    skip_stage = args.skip_stage
    random_state = args.random_state

    print(f"\nConfiguration:")
    print(f"  Input dataset: {input_path}")
    print(f"  Output directory: {output_dir}")
    print(f"  Random state: {random_state}")
    if skip_stage:
        print(f"  Skipping stage: {skip_stage}")

    # Verify input file exists
    if not os.path.exists(input_path):
        print(f"\n[ERROR] Input file not found: {input_path}")
        print("Please provide a valid path to Dataset.csv")
        sys.exit(1)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Track execution
    pipeline_start = time.time()
    stages_run = []
    stage_times = {}
    all_success = True

    # Stage 1: Preprocessing
    if skip_stage != 1:
        # Load module and run
        preprocess_spec.loader.exec_module(preprocess_module)

        # Override sys.argv for stage script argument parsing
        original_argv = sys.argv
        sys.argv = [
            "1_preprocess.py",
            "--input", input_path,
            "--output", output_dir,
            "--random-state", str(random_state)
        ]

        elapsed, success = run_stage(
            1,
            "Dataset Preprocessing",
            preprocess_module.main,
            {}
        )

        sys.argv = original_argv
        stages_run.append((1, "Preprocessing", success))
        stage_times[1] = elapsed
        all_success = all_success and success

        if not success:
            print("\n[ERROR] Stage 1 failed. Stopping pipeline.")
            print("Fix the errors above and try again.")
            sys.exit(1)
    else:
        print("\n[SKIP] Stage 1: Dataset Preprocessing (skipped by user)")

    # Stage 2: Feature Engineering
    if skip_stage != 2:
        # Load module and run
        feature_spec.loader.exec_module(feature_module)

        original_argv = sys.argv
        sys.argv = [
            "2_feature_engineering.py",
            "--input", output_dir,
            "--output", output_dir
        ]

        elapsed, success = run_stage(
            2,
            "Feature Engineering",
            feature_module.main,
            {}
        )

        sys.argv = original_argv
        stages_run.append((2, "Feature Engineering", success))
        stage_times[2] = elapsed
        all_success = all_success and success

        if not success:
            print("\n[ERROR] Stage 2 failed. Stopping pipeline.")
            print("Fix the errors above and try again.")
            sys.exit(1)
    else:
        print("\n[SKIP] Stage 2: Feature Engineering (skipped by user)")

    # Stage 3: Sequence Preparation
    if skip_stage != 3:
        # Load module and run
        sequence_spec.loader.exec_module(sequence_module)

        original_argv = sys.argv
        sys.argv = [
            "3_sequence_preparation.py",
            "--input", output_dir,
            "--output", output_dir
        ]

        elapsed, success = run_stage(
            3,
            "Sequence Preparation",
            sequence_module.main,
            {}
        )

        sys.argv = original_argv
        stages_run.append((3, "Sequence Preparation", success))
        stage_times[3] = elapsed
        all_success = all_success and success

        if not success:
            print("\n[ERROR] Stage 3 failed. Stopping pipeline.")
            print("Fix the errors above and try again.")
            sys.exit(1)
    else:
        print("\n[SKIP] Stage 3: Sequence Preparation (skipped by user)")

    # Calculate total time
    total_time = time.time() - pipeline_start

    # Print final report
    print_final_report(stages_run, stage_times, output_dir, total_time)

    # Exit with appropriate code
    if all_success:
        print("\n[OK] Pipeline completed successfully!")
        print("\nNext steps:")
        print("  - Use train_features.csv for traditional ML models (Random Forest, SVM, XGBoost)")
        print("  - Use train_sequences.npy for deep learning models (LSTM, CNN, hybrid)")
        print("  - Refer to quickstart.md for integration examples")
        sys.exit(0)
    else:
        print("\n[WARNING] Pipeline completed with errors. Check output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
