"""
Custom exceptions for devices app.
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class DeviceAlreadyPairedException(APIException):
    """Exception raised when trying to pair an already paired device."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Device is already paired to a patient. Unpair first or use re-pairing.'
    default_code = 'device_already_paired'


class DeviceNotPairedException(APIException):
    """Exception raised when trying to operate on unpaired device."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Device is not paired to any patient.'
    default_code = 'device_not_paired'


class UnpairedDeviceException(APIException):
    """Exception raised when trying to collect data from unpaired device."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Cannot collect data from unpaired device. Pair device to patient first.'
    default_code = 'unpaired_device'


class InvalidDeviceSerialException(APIException):
    """Exception raised when device serial number format is invalid."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Invalid device serial number format. Must be 8-20 alphanumeric uppercase characters.'
    default_code = 'invalid_device_serial'
