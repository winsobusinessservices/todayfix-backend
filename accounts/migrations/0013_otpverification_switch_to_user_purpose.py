from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0012_merge_20260918_1406'),
    ]

    operations = [
        migrations.AlterField(
            model_name='otpverification',
            name='purpose',
            field=models.CharField(
                choices=[
                    ('SIGNUP', 'Signup'),
                    ('LOGIN', 'Login'),
                    ('PHONE_UPDATE', 'Phone Update'),
                    ('ACCOUNT_DELETION', 'Account Deletion'),
                    ('SWITCH_TO_USER', 'Business Switch To User'),
                ],
                db_index=True,
                default='SIGNUP',
                max_length=20,
            ),
        ),
    ]