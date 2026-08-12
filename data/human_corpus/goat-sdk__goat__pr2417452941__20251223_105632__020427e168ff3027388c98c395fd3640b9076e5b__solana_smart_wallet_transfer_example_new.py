"""
This example shows how to create a Solana Smart Wallet and send a transaction to the network 
using a fireblocks custodial admin signer.

To run this example, you need to set the following environment variables:
- CROSSMINT_API_KEY
- SOLANA_RPC_ENDPOINT
- CROSSMINT_BASE_URL

"""

import os
from goat_wallets.crossmint.solana_smart_wallet import SolanaSmartWalletClient
from goat_wallets.crossmint.parameters import CoreSignerType
from goat_wallets.crossmint.solana_smart_wallet_factory import SolanaSmartWalletFactory
from goat_wallets.crossmint.types import SolanaKeypairSigner
from goat_wallets.crossmint.solana_smart_wallet import SolanaSmartWalletConfig
from solana.rpc.api import Client as SolanaClient
from goat_wallets.crossmint.api_client import CrossmintWalletsAPI
from solders.keypair import Keypair
from dotenv import load_dotenv
from solders.pubkey import Pubkey
from solders.instruction import Instruction
from solders.system_program import TransferParams, transfer
import json

load_dotenv()


def create_send_sol_instruction(sender: str, recipient: str, amount_lamports: int) -> Instruction:
    return transfer(TransferParams(from_pubkey=Pubkey.from_string(sender), to_pubkey=Pubkey.from_string(recipient), lamports=amount_lamports))


def create_wallet(factory: SolanaSmartWalletFactory) -> SolanaSmartWalletClient:
    print("\n🔑 Creating Solana Smart Wallet with fireblocks custodial admin signer...")
    wallet = factory.get_or_create({
        "config": SolanaSmartWalletConfig(
            adminSigner=SolanaKeypairSigner(
                type=CoreSignerType.SOLANA_FIREBLOCKS_CUSTODIAL,
            )
        ),
        "linkedUser": "email:test+1@crossmint.com"
    })
    print(f"✅ Wallet created successfully!")
    print(f"📝 Wallet Address: {wallet.get_address()}")
    print(f"👤 Admin Signer: {wallet.get_admin_signer_address()}")
    return wallet


def send_transfer_transaction(wallet: SolanaSmartWalletClient):
    print("\n💸 Preparing transaction...")
    recipient = Keypair().pubkey()
    instructions = [create_send_sol_instruction(
        wallet.get_address(), wallet.get_address(), 1_000)]
    print(f"📝 Transaction Details:")
    print(f"   From: {wallet.get_address()}")
    print(f"   To: {recipient}")
    print(f"   Amount: 1e-6 SOL")

    print("\n📤 Sending transaction to network...")
    transaction_response = wallet.send_transaction(
        {
            "instructions": instructions,
        }
    )
    print(f"✅ Transaction sent successfully!")
    print(f"🔗 Transaction Hash: {transaction_response.get('hash')}")


def main():
    print("🚀 Starting Solana Smart Wallet Keypair Admin Signer Example")
    print("=" * 50)

    api_key = os.getenv("CROSSMINT_API_KEY")
    base_url = os.getenv("CROSSMINT_BASE_URL",
                         "https://staging.crossmint.com")
    rpc_url = os.getenv("SOLANA_RPC_ENDPOINT",
                        "https://api.devnet.solana.com")
    if not api_key:
        raise ValueError("❌ CROSSMINT_API_KEY is required")

    print("\n🔧 Initializing API client and connection...")
    api_client = CrossmintWalletsAPI(api_key, base_url=base_url)
    connection = SolanaClient(rpc_url)

    factory = SolanaSmartWalletFactory(api_client, connection)
    wallet = create_wallet(factory)

    while True:
        print("🔄 Checking balance...")
        token = "sol"
        balances = wallet.balance_of([token])
        print("💰 Wallet balances:")
        print(json.dumps(balances[0], indent=2))
        sol_balance = next((balance.get("balances", {}).get("total")
                            for balance in balances if balance.get("token") == token))
        if sol_balance is None:
            raise ValueError("❌ No SOL balance found")
        if int(sol_balance) >= 1_000_000:  # 1e-3 SOL
            print("✅ Balance is sufficient. Proceeding to send transaction...")
            break
        print("Your balance is less than 1e-3 SOL. Please fund your wallet using https://faucet.solana.com/ before proceeding.")
        print("Mind that the balance may take a moment to be reflected on your wallet")
        input("Press Enter to continue...")

    send_transfer_transaction(wallet)

    print("\n✨ Example completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    main()
