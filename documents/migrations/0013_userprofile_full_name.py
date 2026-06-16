from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0012_api_keys'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='full_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='ФИО'),
        ),
    ]
