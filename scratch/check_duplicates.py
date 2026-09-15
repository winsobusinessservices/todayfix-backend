import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('''
        SELECT wallet_id, COUNT(*)
        FROM fix_coins_fixcointransaction
        WHERE transaction_type = 'SIGNUP_BONUS'
        GROUP BY wallet_id
        HAVING COUNT(*) > 1;
    ''')
    print('Duplicates:', cursor.fetchall())
