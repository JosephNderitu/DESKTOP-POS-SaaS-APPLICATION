from rest_framework import serializers
from .models import Client, Domain


class ClientAdminSerializer(serializers.ModelSerializer):
    domain = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = ['schema_name', 'name', 'domain', 'subscription_status',
                  'subscription_plan', 'created_on', 'suspended_reason']

    def get_domain(self, obj):
        domain_obj = Domain.objects.filter(tenant=obj, is_primary=True).first()
        return domain_obj.domain if domain_obj else None