from rest_framework import serializers
from .models import ReporterProfile

class ReporterProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReporterProfile
        fields = [
            'phone_number',
            'id_proof_type',
            'id_proof_number',
            'id_proof_document',
            'selfie_photo', 
            'bio', 
            'years_of_experience', 
            'address_line1', 
            'address_line2', 
            'city', 
            'state', 
            'pincode'
        ]
        
        
class ReporterProfileDetailSerializer(serializers.ModelSerializer):
    """Extended serializer for viewing complete reporter profile"""
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    is_kyc_complete = serializers.BooleanField(read_only=True)
    can_submit_stories = serializers.BooleanField(read_only=True)

    class Meta:
        model = ReporterProfile
        fields = '__all__'


class ReporterApprovalSerializer(serializers.Serializer):
    """Serializer for admin approval/rejection actions"""
    action = serializers.ChoiceField(choices=['approve', 'reject', 'suspend', 'reactivate'])
    reason = serializers.CharField(required=False, allow_blank=True)
    admin_notes = serializers.CharField(required=False, allow_blank=True)
    portal_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
