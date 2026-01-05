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
        