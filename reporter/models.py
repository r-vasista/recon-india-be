from django.db import models
from app.models import BaseModel, Portal
from user.models import UserPortalAssignment

from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
User = get_user_model()

# Create your models here.


class ReporterProfile(BaseModel):
    """
    Extended profile for reporters with KYC and verification details
    """
    VERIFICATION_STATUS = (
        ("PENDING", "Pending Verification"),
        ("VERIFIED", "Verified"),
        ("REJECTED", "Rejected"),
    )

    REPORTER_STATUS = (
        ("PENDING", "Pending Approval"),
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("REJECTED", "Rejected"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="reporter_profile")
    
    phone_number = models.CharField(max_length=17, unique=True)
    
    # KYC Documents (Optional)
    id_proof_type = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        choices=(
            ("AADHAAR", "Aadhaar Card"),
            ("PAN", "PAN Card"),
            ("PASSPORT", "Passport"),
            ("DRIVING_LICENSE", "Driving License"),
            ("VOTER_ID", "Voter ID"),
        )
    )
    id_proof_number = models.CharField(max_length=100, null=True, blank=True)
    id_proof_document = models.FileField(upload_to="reporter_kyc/id_proof/", null=True, blank=True)
    
    selfie_photo = models.ImageField(upload_to="reporter_kyc/selfies/", null=True, blank=True)
    
    address_line1 = models.CharField(max_length=255, null=True, blank=True)
    address_line2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=10, null=True, blank=True)
    
    # Verification Status
    kyc_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS, default="PENDING")
    kyc_verified_at = models.DateTimeField(null=True, blank=True)
    kyc_verified_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="verified_reporters"
    )
    
    # Reporter Status
    reporter_status = models.CharField(max_length=20, choices=REPORTER_STATUS, default="PENDING")
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_reporters"
    )
    
    suspended_at = models.DateTimeField(null=True, blank=True)
    suspended_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suspended_reporters"
    )
    suspension_reason = models.TextField(null=True, blank=True)
    
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rejected_reporters"
    )
    rejection_reason = models.TextField(null=True, blank=True)
    
    # Additional Info
    bio = models.TextField(null=True, blank=True, help_text="Brief bio or experience")
    years_of_experience = models.PositiveIntegerField(null=True, blank=True)
    
    # Admin Notes
    admin_notes = models.TextField(null=True, blank=True, help_text="Internal notes for admin review")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone_number"]),
            models.Index(fields=["kyc_status"]),
        ]

    def __str__(self):
        return f"Reporter: {self.user.username} ({self.reporter_status})"

    @property
    def is_kyc_complete(self):
        """Check if all KYC documents are uploaded"""
        return all([
            self.id_proof_document,
            self.selfie_photo
        ])

    @property
    def can_submit_stories(self):
        """Check if reporter can submit stories"""
        return self.reporter_status == "ACTIVE"
