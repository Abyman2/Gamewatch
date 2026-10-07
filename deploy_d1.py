'''
GameWatch Cloudflare D1 Deployment & Migration CLI
==================================================
Author: TSEGA Labs
Usage:
    python deploy_d1.py
    python deploy_d1.py --account-id <ID> --database-id <ID> --token <TOKEN>
'''

import sys
import os
import argparse
import cloudflare_d1


def print_banner():
    print('=' * 68)
    print('  dYZ GAMEWATCH -> CLOUDFLARE D1 AUTOMATED DATABASE DEPLOYMENT')
    print('  100% Free Forever  ?  10GB Edge Storage  ?  Never Sleeps (/mo)')
    print('=' * 68)


def main():
    print_banner()

    parser = argparse.ArgumentParser(description='Deploy GameWatch database to Cloudflare D1')
    parser.add_argument('--account-id', type=str, help='Cloudflare Account ID')
    parser.add_argument('--database-id', type=str, help='Cloudflare D1 Database ID')
    parser.add_argument('--token', type=str, help='Cloudflare API Token with D1:Edit permission')
    parser.add_argument('--save-env', action='store_true', default=True, help='Save credentials to .env file')
    args = parser.parse_args()

    account_id = args.account_id or os.getenv('CLOUDFLARE_ACCOUNT_ID', '').strip()
    database_id = args.database_id or os.getenv('CLOUDFLARE_D1_DATABASE_ID', '').strip()
    api_token = args.token or os.getenv('CLOUDFLARE_API_TOKEN', '').strip()

    # If missing, prompt user interactively
    if not account_id:
        print('\n[Step 1/3] Cloudflare Account ID:')
        print('  (Find this in your Cloudflare dashboard URL: dash.cloudflare.com/<ACCOUNT_ID>)')
        try:
            account_id = input('  Enter Account ID: ').strip()
        except EOFError:
            pass

    if not database_id:
        print('\n[Step 2/3] Cloudflare D1 Database ID:')
        print('  (Find this in Workers & Pages > D1 SQL Database > gamewatch-db)')
        try:
            database_id = input('  Enter Database ID: ').strip()
        except EOFError:
            pass

    if not api_token:
        print('\n[Step 3/3] Cloudflare API Token:')
        print('  (Create at dash.cloudflare.com/profile/api-tokens with D1:Edit permission)')
        try:
            api_token = input('  Enter API Token: ').strip()
        except EOFError:
            pass

    if not (account_id and database_id and api_token):
        print('\n[!] Missing credentials. You can set them via:')
        print('    1. python deploy_d1.py --account-id <id> --database-id <id> --token <token>')
        print('    2. Or populate them in your .env file or Render environment variables.')
        print('\n[i] See DEPLOYMENT_STEPS.md for complete step-by-step instructions.')
        sys.exit(1)

    print('\n[>] Initializing Cloudflare D1 Client...')
    client = cloudflare_d1.CloudflareD1Client(account_id, database_id, api_token)

    # 1. Test Connection
    print('[>] Testing connection to Cloudflare D1 Edge...')
    test_res = client.test_connection()
    if not test_res.get('success'):
        err = test_res.get('error', 'Unknown error')
        print(f'\n[X] Connection failed: {err}')
        print('    Please verify your Account ID, Database ID, and API Token.')
        sys.exit(1)

    print(f'[+] Connected! Cloudflare Timestamp: {test_res.get("cloud_time")}')

    # 2. Initialize Schema
    print('\n[>] Provisioning 16 GameWatch SQL Tables on Cloudflare D1...')
    schema_res = client.init_schema()
    if not schema_res.get('success'):
        errors = schema_res.get('errors')
        print(f'[!] Warning during schema creation: {errors}')
    else:
        created_count = schema_res.get('tables_created')
        print(f'[+] Schema provisioned: {created_count} tables ready.')

    # 3. Synchronize local records
    print('\n[>] Synchronizing local gamewatch.db records to Cloudflare D1...')
    push_res = client.push_local_to_d1('gamewatch.db')
    if push_res.get('success'):
        print('[+] Synchronization complete!')
        for tbl, count in push_res.get('stats', {}).items():
            print(f'    * {tbl:22}: {count} records')
    else:
        sync_err = push_res.get('error')
        print(f'[!] Sync error: {sync_err}')

    # 4. Save to .env
    if args.save_env:
        env_content = f'''# GameWatch Cloudflare D1 Database Configuration
CLOUDFLARE_ACCOUNT_ID={account_id}
CLOUDFLARE_D1_DATABASE_ID={database_id}
CLOUDFLARE_API_TOKEN={api_token}
'''
        try:
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(env_content)
            print('\n[+] Saved credentials to .env (ignored by Git for security).')
        except Exception as e:
            print(f'[!] Could not write .env: {e}')

    masked_token = f"{api_token[:4]}...{api_token[-4:]}" if len(api_token) > 8 else "***"
    # 5. Output Render environment instructions
    print('\n' + '=' * 68)
    print('  GAMEWATCH CLOUDFLARE D1 DEPLOYMENT COMPLETE & OPERATIONAL!')
    print('=' * 68)
    print('\nTo enable permanent 24/7 persistence on your cloud web host (Render):')
    print('1. Go to your Render Dashboard > Web Service (gamewatch)')
    print('2. Click "Environment" in the left sidebar')
    print('3. Add the following 3 Environment Variables:')
    print(f'   * CLOUDFLARE_ACCOUNT_ID      = {account_id}')
    print(f'   * CLOUDFLARE_D1_DATABASE_ID  = {database_id}')
    print(f'   * CLOUDFLARE_API_TOKEN       = {masked_token}')
    print('4. Click "Save Changes". Render will restart with permanent Cloudflare D1 persistence!')
    print('=' * 68 + '\n')
    print('=' * 68 + '\n')


if __name__ == '__main__':
    main()
