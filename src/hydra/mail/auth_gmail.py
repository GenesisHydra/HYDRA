"""
Standalone script to authorize Gmail API and save token to HYDRA Vault.
"""
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

# Import HYDRA Vault
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from hydra.vault import get_vault

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def main():
    vault = get_vault()
    
    # Retrieve client secret from vault
    client_secret_json = vault.get_secret('google/client_secret')
    if client_secret_json is None:
        print("Error: Google client secret not found in vault.")
        print("Please run the migration script or add the client secret to the vault.")
        sys.exit(1)
    
    # Write the client secret to a temporary file for the flow
    # Because InstalledAppFlow.from_client_secrets_file expects a file path.
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(client_secret_json)
        client_secret_path = f.name
    
    try:
        flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            prompt='consent',
            include_granted_scopes=True)
        
        print('Please visit this URL to authorize the application:')
        print(auth_url)
        print()
        code = input('Enter the authorization code: ').strip()
        
        try:
            flow.fetch_token(code=code)
        except Exception as e:
            print(f'Error fetching token: {e}')
            sys.exit(1)
        
        # Save credentials to vault
        token_json = flow.credentials.to_json()
        if vault.set_secret('google/token', token_json):
            print('Token saved successfully to HYDRA Vault.')
        else:
            print('Failed to save token to vault.')
            sys.exit(1)
    finally:
        # Clean up the temporary file
        os.unlink(client_secret_path)

if __name__ == '__main__':
    main()
