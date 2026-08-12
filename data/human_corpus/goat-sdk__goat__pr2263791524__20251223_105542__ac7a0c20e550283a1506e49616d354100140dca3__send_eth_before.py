from decimal import Decimal
from typing import Dict, List, cast

from zon import ZonRecord, ZonString

from goat.classes.plugin_base import PluginBase
from goat.classes.tool_base import ToolBase, create_tool
from goat.utils.create_tool_parameters import create_tool_parameters
from goat.types.chain import Chain

from .evm_smart_wallet_client import EVMWalletClient

class SendETHPlugin(PluginBase[EVMWalletClient]):
    def __init__(self):
        super().__init__("sendETH", [])

    def supports_chain(self, chain: Chain) -> bool:
        return chain["type"] == "evm"

    def get_tools(self, wallet_client: EVMWalletClient) -> List[ToolBase]:
        chain_token = get_chain_token(wallet_client.get_chain()["id"])
        send_tool = create_tool(
            config={
                "name": f"send_{chain_token['symbol']}",
                "description": f"Send {chain_token['symbol']} to an address.",
                "parameters": send_eth_parameters_schema.schema,
            },
            execute_fn=lambda params: send_eth_method(wallet_client, cast(Dict[str, str], params)),
        )
        return [send_tool]


def send_eth() -> SendETHPlugin:
    return SendETHPlugin()

to_param = ZonString()
to_param.description = "The address to send ETH to" # type: ignore
amount_param = ZonString()
amount_param.description = "The amount of ETH to send" # type: ignore

send_eth_parameters_schema = create_tool_parameters(ZonRecord({
    "to": to_param,
    "amount": amount_param
}))

async def send_eth_method(wallet_client: EVMWalletClient, parameters: Dict[str, str]) -> str:
    try:
        # Convert amount to Wei (1 ETH = 10^18 Wei)
        amount = int(Decimal(parameters["amount"]) * Decimal("1e18"))
        tx = await wallet_client.send_transaction({
            "to": parameters["to"],
            "value": amount,
        })
        return tx["hash"]
    except Exception as error:
        chain_token = get_chain_token(wallet_client.get_chain()["id"])
        raise Exception(f"Failed to send {chain_token['symbol']}: {str(error)}")


def get_chain_token(chain_id: int) -> Dict[str, str | int]:
    # This is a simplified version - in a real implementation, you'd want to maintain
    # a mapping of chain IDs to their native currencies, similar to viem/chains
    chain_tokens = {
        1: {"symbol": "ETH", "name": "Ether", "decimals": 18},  # Ethereum Mainnet
        5: {"symbol": "ETH", "name": "Ether", "decimals": 18},  # Goerli
        137: {"symbol": "MATIC", "name": "MATIC", "decimals": 18},  # Polygon
        80001: {"symbol": "MATIC", "name": "MATIC", "decimals": 18},  # Mumbai
        # Add more chains as needed
    }

    if chain_id not in chain_tokens:
        raise Exception(f"Unsupported EVM chain ID: {chain_id}")

    return chain_tokens[chain_id]
