# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0007_rename_initiator_to_signatory'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='auditlog',
            options={
                'ordering': ['-timestamp'],
                'verbose_name': 'Журнал изменений',
                'verbose_name_plural': 'Журнал изменений',
            },
        ),
    ]
