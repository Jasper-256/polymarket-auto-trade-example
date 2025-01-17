from dotenv import set_key, load_dotenv

from helpers.clob_client import create_clob_client


def generate_api_keys():
    client = create_clob_client()

    api_credentials = client.derive_api_key()
    # If this does not work, try client.create_api_key() or client.get_api_key() or client.create_api_key(nonce=1)

    env_path = '.env'  # Path to your .env file
    load_dotenv(env_path)  # Load existing .env file if present

    set_key(env_path, 'CLOB_API_KEY', api_credentials.api_key)
    set_key(env_path, 'CLOB_SECRET', api_credentials.api_secret)
    set_key(env_path, 'CLOB_PASS_PHRASE', api_credentials.api_passphrase)
