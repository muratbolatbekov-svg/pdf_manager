from django.db import migrations, models


def editor_to_manager(apps, schema_editor):
    UserProfile = apps.get_model('documents', 'UserProfile')
    UserProfile.objects.filter(role='editor').update(role='manager')


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0008_alter_auditlog_options'),
    ]

    operations = [
        migrations.RunPython(editor_to_manager, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='userprofile',
            name='role',
            field=models.CharField(
                choices=[
                    ('viewer', 'Читатель'),
                    ('manager', 'Менеджер'),
                    ('admin', 'Администратор'),
                ],
                default='manager',
                max_length=10,
                verbose_name='Роль',
            ),
        ),
    ]
