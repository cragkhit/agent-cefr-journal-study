import pytest
from unittest.mock import Mock, patch
from goat_wallets.crossmint.api_client import CrossmintWalletsAPI
from goat_wallets.crossmint.parameters import AdminSigner, Call, EVMTypedData, CoreSignerType

@pytest.fixture
def api_client():
    return CrossmintWalletsAPI("test-key", "https://staging.crossmint.com")

@pytest.fixture
def mock_response():
    return Mock()

class TestCrossmintWalletsAPI:
    """Test suite for CrossmintWalletsAPI Python implementation."""

    # Wallet Management Tests
    @patch("requests.request")
    def test_create_smart_wallet(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "type": "evm-smart-wallet",
            "address": "0x123",
            "config": {},
            "createdAt": "2024-01-01"
        }
        mock_request.return_value = mock_response

        result = api_client.create_smart_wallet()
        
        assert result["type"] == "evm-smart-wallet"
        assert result["address"] == "0x123"
        assert "config" in result
        assert "createdAt" in result

        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets" in args[0][1]  # Second arg is URL
        assert "x-api-key" in args[1]["headers"]

    @patch("requests.request")
    def test_create_wallet_with_email(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "type": "base-mpc-wallet",
            "address": "0x123",
            "linkedUser": "email:user@test.com",
            "createdAt": "2024-01-01"
        }
        mock_request.return_value = mock_response

        result = api_client.create_wallet_for_email("user@test.com", "base")
        
        assert result == mock_response.json.return_value

        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets" in args[0][1]  # Second arg is URL
        assert args[1]["json"] == {
            "type": "base-mpc-wallet",
            "linkedUser": "email:user@test.com"
        }
        assert "x-api-key" in args[1]["headers"]

    @patch("requests.request")
    def test_create_wallet_with_twitter(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "type": "base-mpc-wallet",
            "address": "0x123",
            "linkedUser": "x:username",
            "createdAt": "2024-01-01"
        }
        mock_request.return_value = mock_response

        result = api_client.create_wallet_for_twitter("username", "base")
        
        assert result == mock_response.json.return_value

        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets" in args[0][1]  # Second arg is URL
        assert args[1]["json"] == {
            "type": "base-mpc-wallet",
            "linkedUser": "x:username"
        }
        assert "x-api-key" in args[1]["headers"]

    @patch("requests.request")
    def test_create_wallet_with_phone(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "type": "base-mpc-wallet",
            "address": "0x123",
            "linkedUser": "phone:+1234567890",
            "createdAt": "2024-01-01"
        }
        mock_request.return_value = mock_response

        result = api_client.create_wallet_for_phone("+1234567890", "base")
        
        assert result == mock_response.json.return_value

        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets" in args[0][1]  # Second arg is URL
        assert args[1]["json"] == {
            "type": "base-mpc-wallet",
            "linkedUser": "phone:+1234567890"
        }
        assert "x-api-key" in args[1]["headers"]

    @patch("requests.request")
    def test_create_wallet_with_user_id(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "type": "base-mpc-wallet",
            "address": "0x123",
            "linkedUser": "userId:123",
            "createdAt": "2024-01-01"
        }
        mock_request.return_value = mock_response

        result = api_client.create_wallet_for_user_id("123", "base")
        
        assert result == mock_response.json.return_value

        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets" in args[0][1]  # Second arg is URL
        assert args[1]["json"] == {
            "type": "base-mpc-wallet",
            "linkedUser": "userId:123"
        }
        assert "x-api-key" in args[1]["headers"]

    # Transaction Tests
    @patch("requests.request")
    def test_create_solana_transaction(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "tx123",
            "walletType": "solana-custodial-wallet",
            "status": "pending",
            "params": {
                "transaction": "base58encodedtransaction"
            },
            "createdAt": "2024-01-01"
        }
        mock_request.return_value = mock_response

        result = api_client.create_transaction_for_custodial_wallet(
            "solana:custodial123",
            "base58encodedtransaction"
        )
        
        assert result == mock_response.json.return_value
        
        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets/solana%3Acustodial123/transactions" in args[0][1]
        assert args[1]["json"] == {
            "params": {
                "transaction": "base58encodedtransaction"
            }
        }
        assert "x-api-key" in args[1]["headers"]

    @patch("requests.request")
    def test_solana_message_signatures(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "sig123",
            "walletType": "solana-custodial-wallet",
            "status": "completed",
            "outputSignature": "solanaSignature",
            "approvals": {
                "pending": [],
                "submitted": []
            },
            "createdAt": "2024-01-01"
        }
        mock_request.return_value = mock_response

        result = api_client.sign_message_for_custodial_wallet(
            "solana:custodial123",
            "Hello Solana"
        )
        
        assert result == mock_response.json.return_value
        
        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets/solana%3Acustodial123/signatures" in args[0][1]
        assert args[1]["json"] == {
            "type": "solana-message",
            "params": {
                "message": "Hello Solana"
            }
        }
        assert "x-api-key" in args[1]["headers"]

    @patch("requests.request")
    def test_solana_specific_errors(self, mock_request, api_client, mock_response):
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Invalid transaction",
            "message": "Transaction verification failed"
        }
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.create_transaction_for_custodial_wallet(
                "solana:custodial123",
                "invalidTransaction"
            )
        
        assert "Error 400" in str(exc_info.value)
        assert "Transaction verification failed" in str(exc_info.value)

    @patch("requests.request")
    def test_get_transaction_status(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "tx123",
            "status": "completed",
            "hash": "0xhash"
        }
        mock_request.return_value = mock_response

        result = api_client.check_transaction_status("wallet123", "tx123")
        assert result["status"] == "completed"
        assert result["hash"] == "0xhash"

    # Signing Tests
    @patch("requests.request")
    def test_evm_transaction_with_chain_params(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "tx123",
            "walletType": "evm-smart-wallet",
            "status": "pending",
            "params": {
                "calls": [
                    {
                        "to": "0x456",
                        "value": "0",
                        "data": "0x0",
                    },
                ],
                "chain": "base",
            },
            "createdAt": "2024-01-01",
        }
        mock_request.return_value = mock_response

        result = api_client.create_transaction_for_smart_wallet(
            "0x123",
            [
                {
                    "to": "0x456",
                    "value": "0",
                    "data": "0x0",
                },
            ],
            "base"
        )
        
        assert result == mock_response.json.return_value
        
        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets/0x123/transactions" in args[0][1]
        assert args[1]["json"] == {
            "params": {
                "calls": [
                    {
                        "to": "0x456",
                        "value": "0",
                        "data": "0x0",
                    },
                ],
                "chain": "base",
            }
        }
        assert "x-api-key" in args[1]["headers"]

    @patch("requests.request")
    def test_evm_multi_signature_approvals(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "tx123",
            "walletType": "evm-smart-wallet",
            "status": "pending",
            "params": {
                "calls": [
                    {
                        "to": "0x456",
                        "value": "0",
                        "data": "0x0",
                    },
                ],
                "chain": "base",
            },
            "approvals": {
                "submitted": [
                    {"signer": "0x123", "signature": "0xsig1"},
                    {"signer": "0x456", "signature": "0xsig2"},
                ],
                "pending": [
                    {"signer": "0x789"},
                ],
                "required": 3,
            },
            "createdAt": "2024-01-01",
        }
        mock_request.return_value = mock_response

        result = api_client.approve_transaction("0x123", "tx123", [
            {"signer": "0x123", "signature": "0xsig1"},
            {"signer": "0x456", "signature": "0xsig2"},
        ])
        
        assert result == mock_response.json.return_value
        
        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets/0x123/transactions/tx123/approvals" in args[0][1]
        assert args[1]["json"] == {
            "approvals": [
                {"signer": "0x123", "signature": "0xsig1"},
                {"signer": "0x456", "signature": "0xsig2"},
            ]
        }
        assert "x-api-key" in args[1]["headers"]

    @patch("requests.request")
    def test_evm_batch_transactions(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "tx123",
            "walletType": "evm-smart-wallet",
            "status": "pending",
            "params": {
                "calls": [
                    {
                        "to": "0x456",
                        "value": "1000000000000000000",  # 1 ETH
                        "data": "0x0",
                    },
                    {
                        "to": "0x789",
                        "value": "0",
                        "data": "0xa9059cbb0000000000000000000000001234567890abcdef1234567890abcdef12345678",  # ERC20 transfer
                    },
                ],
                "chain": "base",
            },
            "createdAt": "2024-01-01",
        }
        mock_request.return_value = mock_response

        result = api_client.create_transaction_for_smart_wallet(
            "0x123",
            [
                {
                    "to": "0x456",
                    "value": "1000000000000000000",  # 1 ETH
                    "data": "0x0",
                },
                {
                    "to": "0x789",
                    "value": "0",
                    "data": "0xa9059cbb0000000000000000000000001234567890abcdef1234567890abcdef12345678",  # ERC20 transfer
                },
            ],
            "base"
        )
        
        assert result == mock_response.json.return_value
        
        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets/0x123/transactions" in args[0][1]
        assert args[1]["json"] == {
            "params": {
                "calls": [
                    {
                        "to": "0x456",
                        "value": "1000000000000000000",
                        "data": "0x0",
                    },
                    {
                        "to": "0x789",
                        "value": "0",
                        "data": "0xa9059cbb0000000000000000000000001234567890abcdef1234567890abcdef12345678",
                    },
                ],
                "chain": "base",
            }
        }
        assert "x-api-key" in args[1]["headers"]

    # NFT Tests
    @patch("requests.request")
    def test_evm_specific_errors(self, mock_request, api_client, mock_response):
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Invalid transaction",
            "message": "Insufficient balance for gas * price + value",
        }
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.create_transaction_for_smart_wallet(
                "0x123",
                [{
                    "to": "0x456",
                    "value": "1000000000000000000000",  # 1000 ETH
                    "data": "0x0",
                }],
                "base"
            )
        
        assert "Error 400" in str(exc_info.value)
        assert "Insufficient balance" in str(exc_info.value)

    @patch("requests.request")
    def test_evm_chain_validation(self, mock_request, api_client, mock_response):
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Invalid chain",
            "message": "Unsupported chain specified",
        }
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.create_transaction_for_smart_wallet(
                "0x123",
                [{
                    "to": "0x456",
                    "value": "0",
                    "data": "0x0",
                }],
                "invalid-chain"
            )
        
        assert "Error 400" in str(exc_info.value)
        assert "Unsupported chain" in str(exc_info.value)

    @patch("requests.request")
    def test_get_collections(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "collections": [{
                "id": "col123",
                "name": "Test Collection",
                "chain": "polygon"
            }]
        }
        mock_request.return_value = mock_response

        result = api_client.get_all_collections()
        assert len(result["collections"]) == 1
        assert result["collections"][0]["id"] == "col123"

    @patch("requests.request")
    def test_mint_nft(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "mint123",
            "status": "pending",
            "tokenId": "1"
        }
        mock_request.return_value = mock_response

        result = api_client.mint_nft(
            collection_id="col123",
            recipient="0x123",
            metadata={"name": "Test NFT"}
        )
        
        assert result["id"] == "mint123"
        assert result["status"] == "pending"

    # Faucet Tests
    @patch("requests.request")
    def test_request_faucet_tokens(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "success",
            "message": "Balance topped up successfully"
        }
        mock_request.return_value = mock_response

        result = api_client.request_faucet_tokens("0x123", "ethereum")
        assert result["status"] == "success"

    # Error Handling Tests
    @patch("requests.request")
    def test_invalid_parameters(self, mock_request, api_client, mock_response):
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Invalid request",
            "message": "Missing required parameter: chain"
        }
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.create_transaction_for_smart_wallet(
                "0x123",
                [{
                    "to": "0x456",
                    "value": "0",
                    "data": "0x0",
                }],
                None  # Missing required chain parameter
            )
        
        assert "Error 400" in str(exc_info.value)
        assert "Missing required parameter" in str(exc_info.value)

    @patch("requests.request")
    def test_rate_limiting(self, mock_request, api_client, mock_response):
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": "Too Many Requests",
            "message": "Rate limit exceeded. Please try again in 60 seconds.",
            "retryAfter": 60
        }
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.create_smart_wallet()
        
        assert "Error 429" in str(exc_info.value)
        assert "Rate limit exceeded" in str(exc_info.value)

    @patch("requests.request")
    def test_network_error(self, mock_request, api_client):
        mock_request.side_effect = Exception("Network error: Connection refused")
        
        with pytest.raises(Exception) as exc_info:
            api_client.create_smart_wallet()
        
        assert "Network error" in str(exc_info.value)
        assert "Connection refused" in str(exc_info.value)

    @patch("requests.request")
    def test_timeout_error(self, mock_request, api_client):
        mock_request.side_effect = Exception("Request timed out after 30 seconds")
        
        with pytest.raises(Exception) as exc_info:
            api_client.create_smart_wallet()
        
        assert "timed out" in str(exc_info.value)

    @patch("requests.request")
    def test_chain_validation_error(self, mock_request, api_client, mock_response):
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Chain validation failed",
            "message": "Chain 'invalid-chain' is not supported. Supported chains are: base, polygon, optimism",
            "supportedChains": ["base", "polygon", "optimism"]
        }
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.create_transaction_for_smart_wallet(
                "0x123",
                [{
                    "to": "0x456",
                    "value": "0",
                    "data": "0x0",
                }],
                "invalid-chain"
            )
        
        assert "Error 400" in str(exc_info.value)
        assert "Chain validation failed" in str(exc_info.value)
        assert "Supported chains" in str(exc_info.value)

    # Authentication Tests
    @patch("requests.request")
    def test_create_collection(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "col123",
            "name": "Test Collection",
            "chain": "ethereum"
        }
        mock_request.return_value = mock_response

        result = api_client.create_collection({"name": "Test Collection", "description": "Test Description"}, "ethereum")
        assert result["id"] == "col123"
        assert result["name"] == "Test Collection"

    @patch("requests.request")
    def test_multiple_transaction_approvals(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "tx123",
            "status": "pending",
            "approvals": {
                "submitted": [
                    {"signer": "0x123", "signature": "0xsig1"},
                    {"signer": "0x456", "signature": "0xsig2"}
                ],
                "pending": []
            }
        }
        mock_request.return_value = mock_response

        result = api_client.approve_transaction("wallet123", "tx123", [{"signer": "0x123", "signature": "0xsig1"}, {"signer": "0x456", "signature": "0xsig2"}])
        assert result["status"] == "pending"
        assert len(result["approvals"]["submitted"]) == 2

    @patch("requests.request")
    def test_transaction_status_polling(self, mock_request, api_client, mock_response):
        # First call returns pending
        mock_response.ok = True
        mock_response.json.side_effect = [
            {
                "id": "tx123",
                "status": "pending",
                "hash": None,
            },
            {
                "id": "tx123",
                "status": "completed",
                "hash": "0xhash123",
            }
        ]
        mock_request.return_value = mock_response

        result = api_client.wait_for_transaction("wallet123", "tx123", interval=0.1, max_attempts=2)
        assert result["status"] == "completed"
        assert result["hash"] == "0xhash123"

    @patch("requests.request")
    def test_signature_verification_polling(self, mock_request, api_client, mock_response):
        # First call returns pending, second call returns completed
        mock_response.ok = True
        mock_response.json.side_effect = [
            {
                "id": "sig123",
                "status": "pending",
                "outputSignature": None,
            },
            {
                "id": "sig123",
                "status": "completed",
                "outputSignature": "0xsig123",
            }
        ]
        mock_request.return_value = mock_response

        result = api_client.wait_for_signature("wallet123", "sig123", interval=0.1, max_attempts=2)
        assert result["status"] == "completed"
        assert result["outputSignature"] == "0xsig123"

    @patch("requests.request")
    def test_action_completion_waiting(self, mock_request, api_client, mock_response):
        # First call returns pending, second call returns succeeded
        mock_response.ok = True
        mock_response.json.side_effect = [
            {
                "status": "pending",
                "data": None,
            },
            {
                "status": "succeeded",
                "data": {
                    "result": "success",
                },
            }
        ]
        mock_request.return_value = mock_response

        result = api_client.wait_for_action("action123", interval=0.1, max_attempts=2)
        assert result["status"] == "succeeded"
        assert result["data"]["result"] == "success"

    @patch("requests.request")
    def test_transaction_polling_timeout(self, mock_request, api_client, mock_response):
        # Always return pending
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "tx123",
            "status": "pending",
            "hash": None,
        }
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.wait_for_transaction("wallet123", "tx123", interval=0.1, max_attempts=2)
        assert "Timed out waiting for transaction" in str(exc_info.value)

    @patch("requests.request")
    def test_signature_verification_timeout(self, mock_request, api_client, mock_response):
        # Always return pending
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "sig123",
            "status": "pending",
            "outputSignature": None,
        }
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.wait_for_signature("wallet123", "sig123", interval=0.1, max_attempts=2)
        assert "Timed out waiting for signature" in str(exc_info.value)

    @patch("requests.request")
    def test_action_completion_timeout(self, mock_request, api_client, mock_response):
        # Always return pending
        mock_response.ok = True
        mock_response.json.return_value = {
            "status": "pending",
            "data": None,
        }
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.wait_for_action("action123", interval=0.1, max_attempts=2)
        assert "Timed out waiting for action" in str(exc_info.value)

    @patch("requests.request")
    def test_api_key_authentication(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        api_client.create_smart_wallet()

        args = mock_request.call_args
        headers = args[1]["headers"]
        assert "x-api-key" in headers
        assert headers["x-api-key"] == "test-key"

    @patch("requests.request")
    def test_invalid_authentication(self, mock_request, api_client, mock_response):
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.json.return_value = {
            "error": "Unauthorized",
            "message": "Invalid API key"
        }
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.create_smart_wallet()
        
        assert "Error 401" in str(exc_info.value)
        assert "Invalid API key" in str(exc_info.value)

    @patch("requests.request")
    def test_admin_signer_configuration(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "tx123",
            "walletType": "evm-smart-wallet",
            "status": "pending",
            "params": {
                "calls": [
                    {
                        "to": "0x456",
                        "value": "0",
                        "data": "0x0",
                    },
                ],
                "chain": "base",
            },
            "approvals": {
                "submitted": [],
                "pending": [
                    {"signer": "admin:0x123"},
                ],
                "required": 1,
            },
            "createdAt": "2024-01-01",
        }
        mock_request.return_value = mock_response

        admin_signer = AdminSigner(
            type=CoreSignerType.EVM_KEYPAIR,
            address="0x123",
            signature="0xsig1",
            chain="base"
        )
        result = api_client.approve_transaction("0x123", "tx123", [admin_signer])
        
        assert result == mock_response.json.return_value
        
        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets/0x123/transactions/tx123/approvals" in args[0][1]
        assert args[1]["json"] == {
            "approvals": [
                {
                    "signer": "admin:0x123",
                    "signature": "0xsig1",
                    "chain": "base"
                }
            ]
        }
        assert "x-api-key" in args[1]["headers"]

    @patch("requests.request")
    def test_signer_validation(self, mock_request, api_client, mock_response):
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "error": "Invalid signer",
            "message": "Signer not authorized for this wallet"
        }
        mock_request.return_value = mock_response

        admin_signer = AdminSigner(
            type=CoreSignerType.EVM_KEYPAIR,
            address="0x123",
            signature="0xsig1",
            chain="base"
        )
        with pytest.raises(Exception) as exc_info:
            api_client.approve_transaction("0x123", "tx123", [admin_signer])
        
        assert "Error 400" in str(exc_info.value)
        assert "Signer not authorized" in str(exc_info.value)
