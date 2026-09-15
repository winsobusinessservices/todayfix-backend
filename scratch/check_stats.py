import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.db import connection
with connection.cursor() as cursor:
    cursor.execute('SELECT COUNT(*) FROM fix_coins_fixcoinwallet;')
    print('Wallets:', cursor.fetchone()[0])
    cursor.execute("SELECT COUNT(*) FROM fix_coins_fixcointransaction WHERE transaction_type = 'SIGNUP_BONUS';")
    print('Bonus Txns:', cursor.fetchone()[0])
    cursor.execute('SELECT COUNT(*) FROM accounts_customuser;')
    print('Users:', cursor.fetchone()[0])
    
    cursor.execute('SELECT wallet_uuid, user_id, available_coins, lifetime_earned_coins FROM fix_coins_fixcoinwallet LIMIT 5;')
    print('Wallet Sample:', cursor.fetchall())
    
    cursor.execute("SELECT transaction_uuid, wallet_id, coins, balance_before, balance_after FROM fix_coins_fixcointransaction WHERE transaction_type = 'SIGNUP_BONUS' LIMIT 5;")
    print('Txn Sample:', cursor.fetchall())
