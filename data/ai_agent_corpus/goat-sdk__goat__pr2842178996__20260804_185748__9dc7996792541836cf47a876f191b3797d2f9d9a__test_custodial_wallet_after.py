import pytest
from base58 import b58encode
from solders.instruction import Instruction
from solders.pubkey import Pubkey
from solders.message import Message
from goat_wallets.crossmint import CustodialSolanaWalletClient
from .utils.helpers import (
    compare_wallet_responses,
    compare_transaction_responses,
    compare_signature_responses,
    compare_error_responses
)


def test_custodial_wallet_creation_with_email(custodial_api, test_email, solana_connection):
    """Test custodial wallet creation with email."""
    # Create wallet
    wallet = custodial_api.create_custodial_wallet(test_email)
    assert wallet["type"] == "solana-mpc-wallet"
    
    # Verify retrieval
    retrieved = custodial_api.get_wallet(f"email:{test_email}:solana-mpc-wallet")
    compare_wallet_responses(wallet, retrieved)
    
    # Test client creation
    client = CustodialSolanaWalletClient(
        wallet["address"],
        custodial_api,
        solana_connection,
        {"email": test_email}
    )
    assert client.get_address() == wallet["address"]


def test_custodial_wallet_creation_with_phone(custodial_api, test_phone, solana_connection):
    """Test custodial wallet creation with phone number."""
    # Create wallet
    wallet = custodial_api.create_custodial_wallet(test_phone)
    assert wallet["type"] == "solana-mpc-wallet"
    
    # Verify retrieval
    retrieved = custodial_api.get_wallet(f"phone:{test_phone}:solana-mpc-wallet")
    compare_wallet_responses(wallet, retrieved)
    
    # Test client creation
    client = CustodialSolanaWalletClient(
        wallet["address"],
        custodial_api,
        solana_connection,
        {"phone": test_phone}
    )
    assert client.get_address() == wallet["address"]


def test_custodial_wallet_creation_with_user_id(custodial_api, test_user_id, solana_connection):
    """Test custodial wallet creation with user ID."""
    # Create wallet
    wallet = custodial_api.create_custodial_wallet(str(test_user_id))
    assert wallet["type"] == "solana-mpc-wallet"
    
    # Verify retrieval
    retrieved = custodial_api.get_wallet(f"userId:{test_user_id}:solana-mpc-wallet")
    compare_wallet_responses(wallet, retrieved)
    
    # Test client creation
    client = CustodialSolanaWalletClient(
        wallet["address"],
        custodial_api,
        solana_connection,
        {"userId": test_user_id}
    )
    assert client.get_address() == wallet["address"]


def test_custodial_wallet_message_signing(custodial_api, test_email, test_message, solana_connection):
    """Test message signing with custodial wallet."""
    # Create wallet and client
    wallet = custodial_api.create_custodial_wallet(test_email)
    client = CustodialSolanaWalletClient(
        wallet["address"],
        custodial_api,
        solana_connection,
        {"email": test_email}
    )
    
    # Sign message
    signature = client.sign_message(test_message)
    assert "signature" in signature
    assert len(signature["signature"]) > 0  # Should be base58 encoded


def test_custodial_wallet_transaction(custodial_api, test_email, solana_connection):
    """Test transaction sending with custodial wallet."""
    # Create wallet and client
    wallet = custodial_api.create_custodial_wallet(test_email)
    client = CustodialSolanaWalletClient(
        wallet["address"],
        custodial_api,
        solana_connection,
        {"email": test_email}
    )
    
    # Create a simple transfer instruction
    instruction = Instruction(
        program_id=Pubkey.from_string("11111111111111111111111111111111"),  # System program
        accounts=[{
            "pubkey": Pubkey.from_string(wallet["address"]),
            "is_signer": True,
            "is_writable": True
        }],
        data=bytes()  # Empty for test
    )
    
    # Send transaction
    tx = client.send_transaction({
        "instructions": [instruction]
    })
    assert tx["status"] in ["success", "pending"]
    if tx["status"] == "success":
        assert len(tx["hash"]) > 0


def test_custodial_wallet_raw_transaction(custodial_api, test_email, solana_connection):
    """Test sending raw transaction with custodial wallet."""
    # Create wallet and client
    wallet = custodial_api.create_custodial_wallet(test_email)
    client = CustodialSolanaWalletClient(
        wallet["address"],
        custodial_api,
        solana_connection,
        {"email": test_email}
    )
    
    # Create a simple message
    instruction = Instruction(
        program_id=Pubkey.from_string("11111111111111111111111111111111"),  # System program
        accounts=[{
            "pubkey": Pubkey.from_string(wallet["address"]),
            "is_signer": True,
            "is_writable": True
        }],
        data=bytes()  # Empty for test
    )
    message = Message(
        instructions=[instruction],
        payer=Pubkey.from_string(wallet["address"])
    )
    
    # Serialize and encode
    serialized = b58encode(bytes(message)).decode()
    
    # Send raw transaction
    tx = client.send_raw_transaction(serialized)
    assert tx["status"] in ["success", "pending"]
    if tx["status"] == "success":
        assert len(tx["hash"]) > 0


def test_custodial_wallet_balance(custodial_api, test_email, solana_connection):
    """Test getting wallet balance."""
    # Create wallet and client
    wallet = custodial_api.create_custodial_wallet(test_email)
    client = CustodialSolanaWalletClient(
        wallet["address"],
        custodial_api,
        solana_connection,
        {"email": test_email}
    )
    
    # Get balance
    balance = client.balance_of(wallet["address"])
    assert "value" in balance
    assert "symbol" in balance
    assert balance["symbol"] == "SOL"
    assert "decimals" in balance
    assert balance["decimals"] == 9
    assert "name" in balance
    assert balance["name"] == "Solana"
    assert "in_base_units" in balance


@pytest.mark.parametrize("invalid_options", [
    {"email": "invalid@email"},
    {"phone": "invalid-phone"},
    {"userId": "invalid-id"}
])
def test_custodial_wallet_invalid_options(custodial_api, invalid_options, solana_connection):
    """Test error handling with invalid options."""
    with pytest.raises(Exception) as exc:
        custodial_api.create_custodial_wallet(list(invalid_options.values())[0])
    assert "error" in str(exc.value).lower() or "invalid" in str(exc.value).lower()


def test_custodial_wallet_invalid_transaction(custodial_api, test_email, solana_connection):
    """Test error handling with invalid transaction."""
    # Create wallet and client
    wallet = custodial_api.create_custodial_wallet(test_email)
    client = CustodialSolanaWalletClient(
        wallet["address"],
        custodial_api,
        solana_connection,
        {"email": test_email}
    )
    
    # Try to send invalid transaction
    with pytest.raises(Exception) as exc:
        client.send_raw_transaction("invalid-transaction")
    assert "error" in str(exc.value).lower() or "invalid" in str(exc.value).lower()
