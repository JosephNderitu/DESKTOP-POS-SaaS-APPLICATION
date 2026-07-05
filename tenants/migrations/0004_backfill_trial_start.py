# tenants/migrations/0004_backfill_trial_start.py
from django.db import migrations
from django.db import models

def backfill_trial_start(apps, schema_editor):
    Client = apps.get_model('tenants', 'Client')
    Client.objects.filter(trial_start_date__isnull=True).update(trial_start_date=models.F('created_on'))

class Migration(migrations.Migration):
    dependencies = [('tenants', '0003_platformauditlog_client_trial_period_days_and_more')]
    operations = [migrations.RunPython(backfill_trial_start, migrations.RunPython.noop)]