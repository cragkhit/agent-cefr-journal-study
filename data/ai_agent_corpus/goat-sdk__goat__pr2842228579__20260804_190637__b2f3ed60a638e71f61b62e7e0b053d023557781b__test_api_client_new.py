import pytest
from unittest.mock import Mock, patch
from goat_wallets.crossmint.api_client import CrossmintWalletsAPI
from goat_wallets.crossmint.parameters import AdminSigner, Call, EVMTypedData

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
    def test_create_custodial_wallet(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "type": "solana-custodial-wallet",
            "address": "solana123",
            "linkedUser": "user@test.com",
            "createdAt": "2024-01-01"
        }
        mock_request.return_value = mock_response

        result = api_client.create_custodial_wallet("user@test.com")
        
        assert result["type"] == "solana-custodial-wallet"
        assert result["address"] == "solana123"
        assert result["linkedUser"] == "user@test.com"

        # Verify request
        mock_request.assert_called_once()
        args = mock_request.call_args
        assert args[0][0] == "POST"  # First arg is method
        assert "/wallets" in args[0][1]  # Second arg is URL
        assert "linkedUser" in args[1]["json"]

    # Transaction Tests
    @patch("requests.request")
    def test_create_transaction(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "tx123",
            "walletType": "evm-smart-wallet",
            "status": "pending",
            "params": {
                "calls": [{
                    "to": "0x456",
                    "value": "0",
                    "data": "0x0"
                }]
            },
            "createdAt": "2024-01-01"
        }
        mock_request.return_value = mock_response

        call = Call(to="0x456", value="0", data="0x0")
        result = api_client.create_transaction_for_smart_wallet(
            "0x123",
            [call],
            "ethereum"
        )
        
        assert result["id"] == "tx123"
        assert result["walletType"] == "evm-smart-wallet"
        assert result["status"] == "pending"
        assert result["params"]["calls"][0]["to"] == "0x456"

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
    def test_sign_message(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "sig123",
            "walletType": "evm-smart-wallet",
            "status": "completed",
            "outputSignature": "0xsig",
            "approvals": {
                "pending": [],
                "submitted": []
            },
            "createdAt": "2024-01-01"
        }
        mock_request.return_value = mock_response

        result = api_client.sign_message_for_smart_wallet(
            "0x123",
            "Hello",
            "ethereum"
        )
        
        assert result["id"] == "sig123"
        assert result["outputSignature"] == "0xsig"
        assert result["status"] == "completed"

    @patch("requests.request")
    def test_sign_typed_data(self, mock_request, api_client, mock_response):
        typed_data = EVMTypedData(
            types={
                "EIP712Domain": [{"name": "name", "type": "string"}],
                "Message": [{"name": "content", "type": "string"}]
            },
            primaryType="Message",
            domain={"name": "Test", "version": "1"},
            message={"content": "Hello"}
        )

        mock_response.ok = True
        mock_response.json.return_value = {
            "id": "sig123",
            "status": "completed",
            "outputSignature": "0xsig"
        }
        mock_request.return_value = mock_response

        result = api_client.sign_typed_data_for_smart_wallet(
            "0x123",
            typed_data,
            "ethereum",
            "evm-keypair:0x123"
        )
        
        assert result["id"] == "sig123"
        assert result["outputSignature"] == "0xsig"

    # NFT Tests
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
    def test_error_handling(self, mock_request, api_client, mock_response):
        mock_response.ok = False
        mock_response.status_code = 400
        mock_response.reason = "Bad Request"
        mock_response.json.return_value = {
            "error": "Invalid request",
            "message": "Bad parameters"
        }
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.create_smart_wallet()
        
        assert "Error 400" in str(exc_info.value)

    @patch("requests.request")
    def test_network_error(self, mock_request, api_client):
        mock_request.side_effect = Exception("Network error")
        
        with pytest.raises(Exception) as exc_info:
            api_client.create_smart_wallet()
        
        assert "Network error" in str(exc_info.value)

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
    def test_action_timeout(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {"status": "pending"}
        mock_request.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            api_client.wait_for_action("action123", max_attempts=2)
        assert "Timed out" in str(exc_info.value)

    @patch("requests.request")
    def test_auth_headers(self, mock_request, api_client, mock_response):
        mock_response.ok = True
        mock_response.json.return_value = {}
        mock_request.return_value = mock_response

        api_client.create_smart_wallet()

        args = mock_request.call_args
        headers = args[1]["headers"]
        assert "x-api-key" in headers
        assert headers["x-api-key"] == "test-key"
