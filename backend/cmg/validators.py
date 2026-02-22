"""
Validation helpers for CMG gimbal servo control (Feature 028).

Used by both GimbalCalibration.clean() and DRF serializer validate() methods
to avoid duplicating bounds-checking logic.
"""
from django.core.exceptions import ValidationError
from decouple import config


def validate_angle_in_range(value, min_deg, max_deg, axis_name):
    """
    Raise ValidationError if value is outside [min_deg, max_deg].

    Args:
        value:     Angle in degrees to validate.
        min_deg:   Minimum allowed angle (inclusive).
        max_deg:   Maximum allowed angle (inclusive).
        axis_name: Human-readable axis name for the error message (e.g. 'pitch_deg').
    """
    if value < min_deg:
        raise ValidationError(
            f"{axis_name} {value} is below configured minimum of {min_deg} for this device."
        )
    if value > max_deg:
        raise ValidationError(
            f"{axis_name} {value} exceeds configured maximum of {max_deg} for this device."
        )


def validate_calibration_bounds(data):
    """
    Validate calibration range fields as a group.

    Checks:
    - pitch_min_deg < pitch_max_deg (strictly less than)
    - roll_min_deg  < roll_max_deg  (strictly less than)
    - rate_limit_deg_per_sec within [GIMBAL_RATE_LIMIT_MIN, GIMBAL_RATE_LIMIT_MAX]

    Args:
        data: dict with keys pitch_min_deg, pitch_max_deg, roll_min_deg,
              roll_max_deg, rate_limit_deg_per_sec.

    Raises:
        ValidationError: dict-style error mapping field name → list of messages,
                         suitable for DRF serializer raise_exception.
    """
    errors = {}

    pitch_min = data.get('pitch_min_deg')
    pitch_max = data.get('pitch_max_deg')
    roll_min = data.get('roll_min_deg')
    roll_max = data.get('roll_max_deg')
    rate_limit = data.get('rate_limit_deg_per_sec')

    if pitch_min is not None and pitch_max is not None:
        if pitch_min >= pitch_max:
            errors['pitch_min_deg'] = [
                f"pitch_min_deg ({pitch_min}) must be strictly less than pitch_max_deg ({pitch_max})."
            ]

    if roll_min is not None and roll_max is not None:
        if roll_min >= roll_max:
            errors['roll_min_deg'] = [
                f"roll_min_deg ({roll_min}) must be strictly less than roll_max_deg ({roll_max})."
            ]

    if rate_limit is not None:
        system_min = config('GIMBAL_RATE_LIMIT_MIN_DEG_PER_SEC', default=5.0, cast=float)
        system_max = config('GIMBAL_RATE_LIMIT_MAX_DEG_PER_SEC', default=180.0, cast=float)
        if rate_limit < system_min:
            errors['rate_limit_deg_per_sec'] = [
                f"Rate limit cannot be below system minimum of {system_min} deg/s."
            ]
        elif rate_limit > system_max:
            errors['rate_limit_deg_per_sec'] = [
                f"Rate limit cannot exceed system maximum of {system_max} deg/s."
            ]

    if errors:
        raise ValidationError(errors)


def validate_pid_gains(data):
    """
    Validate PID gain values against per-axis safe operating bounds.

    Bounds are read from environment variables; all gains must be ≥ 0 and
    ≤ the per-axis maximum defined in .env.

    Args:
        data: dict with keys kp_pitch, ki_pitch, kd_pitch,
              kp_roll, ki_roll, kd_roll.

    Raises:
        ValidationError: dict-style error mapping field name → error message.
    """
    errors = {}

    kp_pitch_max = config('PID_KP_PITCH_MAX', default=0.20, cast=float)
    ki_pitch_max = config('PID_KI_PITCH_MAX', default=0.020, cast=float)
    kd_pitch_max = config('PID_KD_PITCH_MAX', default=0.050, cast=float)
    kp_roll_max  = config('PID_KP_ROLL_MAX',  default=0.15,  cast=float)
    ki_roll_max  = config('PID_KI_ROLL_MAX',  default=0.015, cast=float)
    kd_roll_max  = config('PID_KD_ROLL_MAX',  default=0.040, cast=float)

    bounds = {
        'kp_pitch': (0.0, kp_pitch_max),
        'ki_pitch': (0.0, ki_pitch_max),
        'kd_pitch': (0.0, kd_pitch_max),
        'kp_roll':  (0.0, kp_roll_max),
        'ki_roll':  (0.0, ki_roll_max),
        'kd_roll':  (0.0, kd_roll_max),
    }

    for field, (lo, hi) in bounds.items():
        value = data.get(field)
        if value is None:
            continue
        if value < lo:
            errors[field] = f"{field} ({value}) must be ≥ {lo}."
        elif value > hi:
            errors[field] = f"{field} ({value}) exceeds maximum of {hi}."

    if errors:
        raise ValidationError(errors)
