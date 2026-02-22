"""
Analytics Views

Feature 003: Analytics and Reporting
API views for tremor statistics and PDF report generation.
"""

from datetime import datetime, date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.http import Http404

from patients.models import Patient, DoctorPatientAssignment
from analytics.services.statistics import StatisticsService
from analytics.services.dashboard import DashboardService
from analytics.serializers import StatisticsResponseSerializer, DashboardStatsSerializer


class StandardResultsPagination(PageNumberPagination):
    """
    Standard pagination for analytics results.

    Per spec: Default 50 results per page, max 100.
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class DashboardStatsView(APIView):
    """
    GET /api/analytics/dashboard/

    Feature 032: Dashboard Overview Page

    Returns system-wide summary statistics for the logged-in doctor:
    - total_patients: all patients assigned to this doctor
    - active_devices: devices with status='online' across those patients
    - alerts_count: sessions with severe ML prediction in the last 24 hours
    - tremor_trend: 7-day daily average dominant_amplitude (always 7 entries)

    Access Control:
        - Doctors only

    Returns:
        200: Dashboard statistics
        401: Authentication required (handled by IsAuthenticated)
        403: Doctor role required
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return dashboard stats for the authenticated doctor."""
        if request.user.role != 'doctor':
            return Response(
                {'error': 'Only doctors can access the dashboard.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        stats = DashboardService().get_dashboard_stats(doctor=request.user)
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StatisticsView(APIView):
    """
    GET /api/analytics/stats/

    User Story 1 (P1): Tremor Statistics Aggregation

    Retrieve aggregated tremor statistics for a patient over a specified date range.

    Query Parameters:
        - patient_id (int, required): Patient ID to retrieve statistics for
        - group_by (str, optional): Grouping level ('session' or 'day'), default 'day'
        - start_date (date, optional): Start date (inclusive) in ISO format YYYY-MM-DD
        - end_date (date, optional): End date (inclusive) in ISO format YYYY-MM-DD
        - page (int, optional): Page number for pagination, default 1
        - page_size (int, optional): Results per page, default 50, max 100

    Access Control:
        - Doctors: Can access stats for all assigned patients
        - Patients: Can only access their own statistics

    Returns:
        200: Statistics retrieved successfully (paginated)
        400: Invalid request parameters (missing patient_id, invalid dates, etc.)
        401: Authentication required
        403: User does not have permission to access this patient's data
        404: Patient not found
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    def get(self, request):
        """
        Handle GET request for tremor statistics.
        """
        # T018: Query parameter validation
        patient_id = request.query_params.get('patient_id')
        if not patient_id:
            return Response({
                'error': 'Missing parameter',
                'detail': 'patient_id query parameter is required',
                'code': 'MISSING_PATIENT_ID'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            patient_id = int(patient_id)
        except (ValueError, TypeError):
            return Response({
                'error': 'Invalid parameter',
                'detail': 'patient_id must be a valid integer',
                'code': 'INVALID_PATIENT_ID'
            }, status=status.HTTP_400_BAD_REQUEST)

        # T021: Error handling - patient not found
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({
                'error': 'Patient not found',
                'detail': f'No patient exists with ID {patient_id}',
                'code': 'PATIENT_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        # T017: Patient access control
        user = request.user
        if user.role == 'doctor':
            # Doctors can access assigned patients
            if not DoctorPatientAssignment.objects.filter(
                doctor_id=user.id,
                patient_id=patient_id
            ).exists():
                return Response({
                    'error': 'Access forbidden',
                    'detail': 'You do not have permission to access this patient\'s data',
                    'code': 'PATIENT_ACCESS_FORBIDDEN'
                }, status=status.HTTP_403_FORBIDDEN)
        elif user.role == 'patient':
            # Patients can only access their own data
            try:
                user_patient = Patient.objects.get(user_id=user.id)
                if user_patient.id != patient_id:
                    return Response({
                        'error': 'Access forbidden',
                        'detail': 'You can only access your own statistics',
                        'code': 'PATIENT_ACCESS_FORBIDDEN'
                    }, status=status.HTTP_403_FORBIDDEN)
            except Patient.DoesNotExist:
                return Response({
                    'error': 'Access forbidden',
                    'detail': 'Patient record not found for your account',
                    'code': 'PATIENT_ACCESS_FORBIDDEN'
                }, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({
                'error': 'Access forbidden',
                'detail': 'Only doctors and patients can access statistics',
                'code': 'INVALID_USER_ROLE'
            }, status=status.HTTP_403_FORBIDDEN)

        # T018: Validate group_by parameter
        group_by = request.query_params.get('group_by', 'day')
        if group_by not in ['session', 'day']:
            return Response({
                'error': 'Invalid parameter',
                'detail': 'group_by must be either "session" or "day"',
                'code': 'INVALID_GROUP_BY',
                'field': 'group_by'
            }, status=status.HTTP_400_BAD_REQUEST)

        # T018: Parse and validate date parameters
        start_date = None
        end_date = None

        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            if end_date_str:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return Response({
                'error': 'Invalid date format',
                'detail': 'Dates must be in ISO format YYYY-MM-DD',
                'code': 'INVALID_DATE_FORMAT'
            }, status=status.HTTP_400_BAD_REQUEST)

        # T018: Validate date range
        if start_date and end_date and end_date < start_date:
            return Response({
                'error': 'Invalid date range',
                'detail': 'end_date must be greater than or equal to start_date',
                'code': 'INVALID_DATE_RANGE',
                'field': 'end_date'
            }, status=status.HTTP_400_BAD_REQUEST)

        # T021: Check for future dates
        today = date.today()
        if start_date and start_date > today:
            return Response({
                'error': 'Invalid date',
                'detail': 'start_date cannot be in the future',
                'code': 'FUTURE_DATE',
                'field': 'start_date'
            }, status=status.HTTP_400_BAD_REQUEST)
        if end_date and end_date > today:
            return Response({
                'error': 'Invalid date',
                'detail': 'end_date cannot be in the future',
                'code': 'FUTURE_DATE',
                'field': 'end_date'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calculate statistics using StatisticsService
        try:
            service = StatisticsService(
                patient_id=patient_id,
                start_date=start_date,
                end_date=end_date
            )
            stats_data = service.get_statistics(group_by=group_by)

        except Exception as e:
            # T021: Handle unexpected service errors
            return Response({
                'error': 'Internal server error',
                'detail': 'An error occurred while calculating statistics',
                'code': 'INTERNAL_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # T019: Apply pagination to results
        paginator = self.pagination_class()
        results = stats_data['results']
        paginated_results = paginator.paginate_queryset(results, request)

        # Build response with pagination
        response_data = {
            'count': len(results),
            'next': paginator.get_next_link(),
            'previous': paginator.get_previous_link(),
            'baseline': stats_data['baseline'],
            'results': paginated_results if paginated_results is not None else results
        }

        # T021: Handle no data scenario gracefully (200 with empty results, not 404)
        if not response_data['results']:
            response_data['baseline'] = None  # No baseline if no sessions

        return Response(response_data, status=status.HTTP_200_OK)


class ReportGenerationView(APIView):
    """
    POST /api/analytics/reports/

    User Story 2 (P2): PDF Report Generation

    Generate a comprehensive PDF report containing tremor statistics, charts, and ML predictions.

    Request Body (JSON):
        - patient_id (int, required): Patient ID to generate report for
        - start_date (date, optional): Report start date (inclusive), defaults to earliest session
        - end_date (date, optional): Report end date (inclusive), defaults to today
        - include_charts (bool, optional): Include trend charts in PDF, default true
        - include_ml_summary (bool, optional): Include ML prediction summary, default true

    Access Control:
        - Doctors: Can generate reports for all assigned patients
        - Patients: Can only generate their own reports

    Returns:
        200: PDF report generated successfully (binary file attachment)
        202: Report generation accepted (processing, if async)
        400: Invalid request parameters or insufficient data
        401: Authentication required
        403: User does not have permission to access this patient's data
        500: PDF generation error
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handle POST request for PDF report generation.
        """
        from analytics.serializers import ReportRequestSerializer
        from analytics.services.report_generator import PDFReportGenerator
        from django.http import FileResponse
        import os

        # Validate request data
        serializer = ReportRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'error': 'Invalid request',
                'detail': serializer.errors,
                'code': 'VALIDATION_ERROR'
            }, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        patient_id = validated_data['patient_id']
        start_date = validated_data.get('start_date')
        end_date = validated_data.get('end_date')
        include_charts = validated_data.get('include_charts', True)
        include_ml_summary = validated_data.get('include_ml_summary', True)

        # Verify patient exists
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({
                'error': 'Patient not found',
                'detail': f'No patient exists with ID {patient_id}',
                'code': 'PATIENT_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)

        # T030: Access control (same as statistics endpoint)
        user = request.user
        if user.role == 'doctor':
            # Doctors can access assigned patients
            if not DoctorPatientAssignment.objects.filter(
                doctor_id=user.id,
                patient_id=patient_id
            ).exists():
                return Response({
                    'error': 'Access forbidden',
                    'detail': 'You do not have permission to generate reports for this patient',
                    'code': 'PATIENT_ACCESS_FORBIDDEN'
                }, status=status.HTTP_403_FORBIDDEN)
        elif user.role == 'patient':
            # Patients can only access their own data
            try:
                user_patient = Patient.objects.get(user_id=user.id)
                if user_patient.id != patient_id:
                    return Response({
                        'error': 'Access forbidden',
                        'detail': 'You can only generate reports for yourself',
                        'code': 'PATIENT_ACCESS_FORBIDDEN'
                    }, status=status.HTTP_403_FORBIDDEN)
            except Patient.DoesNotExist:
                return Response({
                    'error': 'Access forbidden',
                    'detail': 'Patient record not found for your account',
                    'code': 'PATIENT_ACCESS_FORBIDDEN'
                }, status=status.HTTP_403_FORBIDDEN)
        else:
            return Response({
                'error': 'Access forbidden',
                'detail': 'Only doctors and patients can generate reports',
                'code': 'INVALID_USER_ROLE'
            }, status=status.HTTP_403_FORBIDDEN)

        # T031, T032, T033, T038: Generate PDF and return as download
        try:
            generator = PDFReportGenerator(
                patient_id=patient_id,
                start_date=start_date,
                end_date=end_date,
                include_charts=include_charts,
                include_ml_summary=include_ml_summary
            )

            pdf_path = generator.generate_pdf()

            # T032: Return PDF as attachment with Content-Disposition header
            pdf_file = open(pdf_path, 'rb')
            filename = os.path.basename(pdf_path)

            response = FileResponse(
                pdf_file,
                content_type='application/pdf',
                as_attachment=True,
                filename=filename
            )

            # T033: Schedule immediate deletion after response is sent
            # Note: FileResponse handles file closing, we'll delete in a finally block
            # For production, use a signal or middleware to ensure cleanup
            def cleanup_pdf():
                try:
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)
                except Exception:
                    pass  # Log error in production

            # Attach cleanup to response (will execute after file is sent)
            response.close = lambda: (pdf_file.close(), cleanup_pdf())

            return response

        except ValueError as e:
            # T038: Handle no data or file size exceeded errors
            error_message = str(e)
            if "No biometric sessions found" in error_message:
                return Response({
                    'error': 'Insufficient data',
                    'detail': error_message,
                    'code': 'NO_DATA_FOR_REPORT'
                }, status=status.HTTP_400_BAD_REQUEST)
            elif "exceeds maximum size" in error_message:
                return Response({
                    'error': 'Report generation failed',
                    'detail': error_message,
                    'code': 'PDF_SIZE_LIMIT_EXCEEDED'
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    'error': 'Report generation failed',
                    'detail': error_message,
                    'code': 'REPORT_GENERATION_ERROR'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # T038: Handle unexpected PDF generation errors
            return Response({
                'error': 'Report generation failed',
                'detail': 'An error occurred while generating the PDF. Please try again.',
                'code': 'PDF_GENERATION_ERROR'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
