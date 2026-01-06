from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from reporter.models import ReporterProfile
from reporter.serializers import (
    ReporterProfileDetailSerializer, ReporterProfileSerializer, ReporterApprovalSerializer
)
from user.models import Role, UserRole, UserPortalAssignment
from user.permissions  import IsReporter, IsAdmin
from app.models import Portal
from app.utils import success_response, error_response


class ReporterProfileAPIView(APIView):
    """
    GET /api/reporter/profile/
    Get current reporter's profile
    
    PUT /api/reporter/profile/
    Update current reporter's profile
    """
    permission_classes = [IsAuthenticated, IsReporter]

    def get(self, request):
        try:
            reporter_profile = ReporterProfile.objects.get(user=request.user)
            serializer = ReporterProfileDetailSerializer(reporter_profile)
            return Response(
                success_response(serializer.data, "Profile retrieved successfully"),
                status=status.HTTP_200_OK
            )
        except ReporterProfile.DoesNotExist:
            return Response(
                error_response("Reporter profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request):
        try:
            reporter_profile = ReporterProfile.objects.get(user=request.user)
            
            serializer = ReporterProfileSerializer(
                reporter_profile,
                data=request.data,
                partial=True
            )
            
            if not serializer.is_valid():
                return Response(
                    error_response(serializer.errors),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer.save()
            
            return Response(
                success_response(serializer.data, "Profile updated successfully"),
                status=status.HTTP_200_OK
            )
            
        except ReporterProfile.DoesNotExist:
            return Response(
                error_response("Reporter profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )


class AdminReporterListAPIView(APIView):
    """
    GET /api/admin/reporters/?status=PENDING&kyc_status=VERIFIED
    List all reporters with optional filtering
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        # Get query parameters for filtering
        reporter_status = request.query_params.get('status')
        kyc_status = request.query_params.get('kyc_status')

        reporters = ReporterProfile.objects.select_related('user').all()

        if reporter_status:
            reporters = reporters.filter(reporter_status=reporter_status.upper())
        
        if kyc_status:
            reporters = reporters.filter(kyc_status=kyc_status.upper())

        serializer = ReporterProfileDetailSerializer(reporters, many=True)
        
        return Response(
            success_response(
                {
                    "count": reporters.count(),
                    "reporters": serializer.data
                },
                "Reporters retrieved successfully"
            ),
            status=status.HTTP_200_OK
        )


class AdminReporterDetailAPIView(APIView):
    """
    GET /api/admin/reporters/<reporter_id>/
    Get specific reporter details with assigned portals
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request, reporter_id):
        try:
            reporter_profile = ReporterProfile.objects.select_related('user').get(id=reporter_id)
            serializer = ReporterProfileDetailSerializer(reporter_profile)
            
            # Include assigned portals
            assigned_portals = UserPortalAssignment.objects.filter(
                user=reporter_profile.user
            ).select_related('portal')
            
            portal_data = [
                {
                    "id": assignment.portal.id,
                    "name": assignment.portal.name
                }
                for assignment in assigned_portals
            ]
            
            response_data = serializer.data
            response_data['assigned_portals'] = portal_data
            
            return Response(
                success_response(response_data, "Reporter details retrieved"),
                status=status.HTTP_200_OK
            )
            
        except ReporterProfile.DoesNotExist:
            return Response(
                error_response("Reporter not found"),
                status=status.HTTP_404_NOT_FOUND
            )


class AdminReporterActionAPIView(APIView):
    """
    POST /api/admin/reporters/<reporter_id>/action/
    
    Example Payloads:
    
    Approve:
    {
        "action": "approve",
        "admin_notes": "Good profile",
        "portal_ids": [1, 2, 3]
    }
    
    Reject:
    {
        "action": "reject",
        "reason": "Incomplete KYC documents"
    }
    
    Suspend:
    {
        "action": "suspend",
        "reason": "Policy violation"
    }
    
    Reactivate:
    {
        "action": "reactivate"
    }
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    @transaction.atomic
    def post(self, request, reporter_id):
        serializer = ReporterApprovalSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(
                error_response(serializer.errors),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            reporter_profile = ReporterProfile.objects.select_related('user').get(id=reporter_id)
        except ReporterProfile.DoesNotExist:
            return Response(
                error_response("Reporter not found"),
                status=status.HTTP_404_NOT_FOUND
            )

        action = serializer.validated_data['action']
        reason = serializer.validated_data.get('reason', '')
        admin_notes = serializer.validated_data.get('admin_notes', '')
        portal_ids = serializer.validated_data.get('portal_ids', [])

        try:
            if action == 'approve':
                reporter_profile.reporter_status = 'ACTIVE'
                reporter_profile.approved_at = timezone.now()
                reporter_profile.approved_by = request.user
                reporter_profile.kyc_status = 'VERIFIED'
                reporter_profile.kyc_verified_at = timezone.now()
                reporter_profile.kyc_verified_by = request.user
                
                # Assign portals if provided
                if portal_ids:
                    portals = Portal.objects.filter(id__in=portal_ids)
                    for portal in portals:
                        UserPortalAssignment.objects.get_or_create(
                            user=reporter_profile.user,
                            portal=portal
                        )
                
                message = "Reporter approved successfully"

            elif action == 'reject':
                if not reason:
                    return Response(
                        error_response("Reason is required for rejection"),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                reporter_profile.reporter_status = 'REJECTED'
                reporter_profile.rejected_at = timezone.now()
                reporter_profile.rejected_by = request.user
                reporter_profile.rejection_reason = reason
                reporter_profile.kyc_status = 'REJECTED'
                message = "Reporter rejected"

            elif action == 'suspend':
                if not reason:
                    return Response(
                        error_response("Reason is required for suspension"),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                reporter_profile.reporter_status = 'SUSPENDED'
                reporter_profile.suspended_at = timezone.now()
                reporter_profile.suspended_by = request.user
                reporter_profile.suspension_reason = reason
                message = "Reporter suspended"

            elif action == 'reactivate':
                reporter_profile.reporter_status = 'ACTIVE'
                reporter_profile.suspended_at = None
                reporter_profile.suspended_by = None
                reporter_profile.suspension_reason = None
                message = "Reporter reactivated"

            # Update admin notes if provided
            if admin_notes:
                reporter_profile.admin_notes = admin_notes

            reporter_profile.save()

            serializer = ReporterProfileDetailSerializer(reporter_profile)
            return Response(
                success_response(serializer.data, message),
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                error_response(f"Action failed: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminReporterAssignPortalsAPIView(APIView):
    """
    POST /api/admin/reporters/<reporter_id>/assign-portals/
    
    Assign or update portals for a reporter
    
    {
        "portal_ids": [1, 2, 3]
    }
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    @transaction.atomic
    def post(self, request, reporter_id):
        try:
            reporter_profile = ReporterProfile.objects.select_related('user').get(id=reporter_id)
        except ReporterProfile.DoesNotExist:
            return Response(
                error_response("Reporter not found"),
                status=status.HTTP_404_NOT_FOUND
            )

        portal_ids = request.data.get('portal_ids', [])
        
        if not portal_ids or not isinstance(portal_ids, list):
            return Response(
                error_response("portal_ids must be a non-empty list"),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Remove existing assignments
            UserPortalAssignment.objects.filter(user=reporter_profile.user).delete()
            
            # Create new assignments
            portals = Portal.objects.filter(id__in=portal_ids)
            
            if len(portals) != len(portal_ids):
                return Response(
                    error_response("Some portal IDs are invalid"),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            for portal in portals:
                UserPortalAssignment.objects.create(
                    user=reporter_profile.user,
                    portal=portal
                )
            
            return Response(
                success_response(
                    {
                        "reporter_id": reporter_id,
                        "assigned_portals": [{"id": p.id, "name": p.name} for p in portals]
                    },
                    "Portals assigned successfully"
                ),
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                error_response(f"Failed to assign portals: {str(e)}"),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
