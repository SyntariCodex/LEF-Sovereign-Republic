"""
LEF Wallet Manager — Sovereign key management.
Handles wallet creation, encrypted key storage, transaction signing.
Uses Base chain (Coinbase L2) as primary network.

Phase 5 Active Tasks — Task 5.1

Security:
  - Private key NEVER in plaintext, NEVER in logs, NEVER in DB
  - Encryption key comes from environment variable LEF_WALLET_KEY only
  - wallet_encrypted.json contains ONLY the encrypted key + public address
  - Fernet symmetric encryption (AES-128-CBC with HMAC)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from eth_account import Account
from cryptography.fernet import Fernet, InvalidToken
from web3 import Web3

BASE_DIR = Path(__file__).parent.parent  # republic/
BRIDGE_DIR = BASE_DIR.parent / "The_Bridge"

logger = logging.getLogger("LEF.WalletManager")


class WalletManager:
    """
    Sovereign wallet management for LEF.
    Creates, loads, and signs transactions with encrypted key storage.
    Primary network: Base (Coinbase L2, chain_id 8453).
    Testnet: Base Sepolia (chain_id 84532).
    """

    WALLET_PATH = os.path.join(str(BRIDGE_DIR), 'wallet_encrypted.json')

    # Network configurations
    NETWORKS = {
        'base': {
            'chain_id': 8453,
            'rpc_url': 'https://mainnet.base.org',
            'explorer': 'https://basescan.org',
            'name': 'Base Mainnet'
        },
        'base_sepolia': {
            'chain_id': 84532,
            'rpc_url': 'https://sepolia.base.org',
            'explorer': 'https://sepolia.basescan.org',
            'name': 'Base Sepolia Testnet'
        }
    }

    def __init__(self, encryption_key: str = None, network: str = 'base_sepolia'):
        """
        Initialize with encryption key from environment variable.
        NEVER hardcode or log the encryption key.

        Args:
            encryption_key: Fernet key for encrypting/decrypting private key.
                           If None, reads from LEF_WALLET_KEY env var.
            network: 'base' for mainnet, 'base_sepolia' for testnet.
        """
        self.encryption_key = encryption_key or os.getenv('LEF_WALLET_KEY')
        if not self.encryption_key:
            raise ValueError(
                "LEF_WALLET_KEY environment variable required. "
                "Generate one with: python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )

        try:
            # Validate the key is a valid Fernet key
            if isinstance(self.encryption_key, str):
                self.fernet = Fernet(self.encryption_key.encode())
            else:
                self.fernet = Fernet(self.encryption_key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")

        self.account = None
        self.wallet_data = None

        # Network setup
        if network not in self.NETWORKS:
            raise ValueError(f"Unknown network: {network}. Use: {list(self.NETWORKS.keys())}")
        self.network = network
        self.network_config = self.NETWORKS[network]
        self.chain_id = self.network_config['chain_id']

        # Web3 provider (lazy init — only connect when needed)
        self._w3 = None

        logger.info(f"[WalletManager] Initialized for network: {self.network_config['name']}")

    @property
    def w3(self) -> Web3:
        """Lazy Web3 provider initialization."""
        if self._w3 is None:
            rpc_url = os.getenv('LEF_RPC_URL', self.network_config['rpc_url'])
            self._w3 = Web3(Web3.HTTPProvider(rpc_url))
            if not self._w3.is_connected():
                logger.warning(f"[WalletManager] Cannot connect to {rpc_url}")
        return self._w3

    @staticmethod
    def generate_encryption_key() -> str:
        """
        Generate a new Fernet encryption key.
        Store this securely in environment variables. NEVER commit to code.
        """
        return Fernet.generate_key().decode()

    def create_wallet(self) -> str:
        """
        Generate new Ethereum-compatible wallet.
        Returns public address. Private key stored encrypted.
        ONLY call this once. If wallet exists, use load_wallet() instead.

        Returns:
            str: The public Ethereum address (checksummed)

        Raises:
            FileExistsError: If wallet file already exists
        """
        if os.path.exists(self.WALLET_PATH):
            raise FileExistsError(
                f"Wallet already exists at {self.WALLET_PATH}. "
                "Use load_wallet() to load it, or delete manually if you want a new one."
            )

        # Generate new account
        account = Account.create()

        # Encrypt private key
        private_key_hex = account.key.hex()
        encrypted_key = self.fernet.encrypt(private_key_hex.encode())

        # Build wallet data (NO plaintext private key)
        self.wallet_data = {
            'address': account.address,
            'encrypted_private_key': encrypted_key.decode(),
            'created': datetime.now().isoformat(),
            'network': self.network,
            'chain_id': self.chain_id,
            'version': 1,
            'note': 'LEF sovereign wallet — private key encrypted with Fernet (AES-128-CBC + HMAC)'
        }

        # Ensure directory exists
        os.makedirs(os.path.dirname(self.WALLET_PATH), exist_ok=True)

        # Write encrypted wallet
        with open(self.WALLET_PATH, 'w') as f:
            json.dump(self.wallet_data, f, indent=2)

        # Set restrictive file permissions (owner read/write only)
        try:
            os.chmod(self.WALLET_PATH, 0o600)
        except OSError:
            logger.warning("[WalletManager] Could not set restrictive file permissions")

        self.account = account
        logger.info(f"[WalletManager] Wallet created: {account.address}")
        logger.info(f"[WalletManager] Network: {self.network_config['name']} (chain_id: {self.chain_id})")

        return account.address

    def load_wallet(self) -> str:
        """
        Load existing wallet from encrypted file.
        Returns public address.

        Returns:
            str: The public Ethereum address (checksummed)

        Raises:
            FileNotFoundError: If wallet file doesn't exist
            ValueError: If decryption fails (wrong key)
        """
        if not os.path.exists(self.WALLET_PATH):
            raise FileNotFoundError(
                f"No wallet found at {self.WALLET_PATH}. "
                "Use create_wallet() to generate one."
            )

        with open(self.WALLET_PATH, 'r') as f:
            self.wallet_data = json.load(f)

        # Decrypt private key
        try:
            encrypted_key = self.wallet_data['encrypted_private_key'].encode()
            decrypted_key = self.fernet.decrypt(encrypted_key).decode()
        except InvalidToken:
            raise ValueError(
                "Failed to decrypt wallet — wrong LEF_WALLET_KEY. "
                "The encryption key must match the one used during wallet creation."
            )

        # Reconstruct account from private key
        self.account = Account.from_key(decrypted_key)

        # Verify address matches stored address
        if self.account.address != self.wallet_data['address']:
            raise ValueError(
                f"Address mismatch: decrypted key gives {self.account.address}, "
                f"but wallet file says {self.wallet_data['address']}. "
                "Wallet file may be corrupted."
            )

        logger.info(f"[WalletManager] Wallet loaded: {self.account.address}")
        return self.account.address

    def get_address(self) -> str:
        """
        Return public address (safe to share/log).

        Returns:
            str: Checksummed Ethereum address, or None if no wallet loaded
        """
        if self.account:
            return self.account.address
        if self.wallet_data:
            return self.wallet_data.get('address')
        return None

    def sign_transaction(self, tx: dict) -> bytes:
        """
        Sign a transaction with LEF's private key.

        Args:
            tx: Transaction dict with fields:
                - to: recipient address
                - value: amount in wei
                - gas: gas limit
                - gasPrice or maxFeePerGas/maxPriorityFeePerGas
                - nonce: transaction nonce
                - chainId: chain ID (defaults to configured chain)
                - data: optional calldata (hex string or bytes)

        Returns:
            bytes: The signed transaction raw bytes (ready to broadcast)

        Raises:
            RuntimeError: If no wallet loaded
            ValueError: If transaction missing required fields
        """
        if not self.account:
            raise RuntimeError("No wallet loaded. Call load_wallet() or create_wallet() first.")

        # Ensure chain ID is set
        if 'chainId' not in tx:
            tx['chainId'] = self.chain_id

        # Safety checks
        if tx.get('chainId') != self.chain_id:
            raise ValueError(
                f"Chain ID mismatch: tx has {tx.get('chainId')}, "
                f"expected {self.chain_id} ({self.network}). "
                "This prevents signing transactions for wrong network."
            )

        # Gas limit safety cap (prevent accidental high gas)
        MAX_GAS_LIMIT = 500_000
        if tx.get('gas', 0) > MAX_GAS_LIMIT:
            raise ValueError(
                f"Gas limit {tx['gas']} exceeds safety cap of {MAX_GAS_LIMIT}. "
                "Reduce gas or increase cap if intentional."
            )

        # Value transfer safety cap (0.1 ETH on mainnet, 10 ETH on testnet)
        max_value_wei = Web3.to_wei(0.1, 'ether') if self.network == 'base' else Web3.to_wei(10, 'ether')
        if tx.get('value', 0) > max_value_wei:
            max_eth = 0.1 if self.network == 'base' else 10
            raise ValueError(
                f"Value transfer exceeds safety cap of {max_eth} ETH. "
                "This cap prevents accidental large transfers."
            )

        # Sign
        signed = self.account.sign_transaction(tx)
        logger.info(f"[WalletManager] Transaction signed (to: {tx.get('to', 'contract creation')})")

        return signed.raw_transaction

    def send_transaction(self, tx: dict) -> str:
        """
        Sign and broadcast a transaction.

        Args:
            tx: Transaction dict (see sign_transaction for fields).
                If 'nonce' is missing, it will be fetched from the network.
                If 'gas' is missing, it will be estimated.

        Returns:
            str: Transaction hash (hex string)

        Raises:
            RuntimeError: If not connected to network
        """
        if not self.account:
            raise RuntimeError("No wallet loaded. Call load_wallet() or create_wallet() first.")

        if not self.w3.is_connected():
            raise RuntimeError(f"Cannot connect to {self.network_config['name']}")

        # Auto-fill nonce if not provided
        if 'nonce' not in tx:
            tx['nonce'] = self.w3.eth.get_transaction_count(self.account.address)

        # Auto-fill gas if not provided
        if 'gas' not in tx:
            try:
                tx['gas'] = self.w3.eth.estimate_gas(tx)
            except Exception as e:
                logger.warning(f"[WalletManager] Gas estimation failed: {e}, using default 100000")
                tx['gas'] = 100_000

        # Auto-fill gas price if not provided
        if 'gasPrice' not in tx and 'maxFeePerGas' not in tx:
            tx['gasPrice'] = self.w3.eth.gas_price

        # Sign and send
        raw_tx = self.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(raw_tx)
        tx_hash_hex = tx_hash.hex()

        logger.info(f"[WalletManager] Transaction sent: {tx_hash_hex}")
        logger.info(f"[WalletManager] Explorer: {self.network_config['explorer']}/tx/0x{tx_hash_hex}")

        return tx_hash_hex

    def get_balance(self) -> dict:
        """
        Check ETH balance on configured network.

        Returns:
            dict: {
                'address': str,
                'balance_wei': int,
                'balance_eth': float,
                'network': str,
                'connected': bool
            }
        """
        if not self.account:
            raise RuntimeError("No wallet loaded. Call load_wallet() or create_wallet() first.")

        result = {
            'address': self.account.address,
            'balance_wei': 0,
            'balance_eth': 0.0,
            'network': self.network_config['name'],
            'connected': False
        }

        try:
            if self.w3.is_connected():
                balance_wei = self.w3.eth.get_balance(self.account.address)
                result['balance_wei'] = balance_wei
                result['balance_eth'] = float(Web3.from_wei(balance_wei, 'ether'))
                result['connected'] = True
        except Exception as e:
            logger.error(f"[WalletManager] Balance check failed: {e}")

        return result

    def wallet_exists(self) -> bool:
        """Check if wallet file exists."""
        return os.path.exists(self.WALLET_PATH)

    def get_wallet_info(self) -> dict:
        """
        Return non-sensitive wallet metadata.
        Safe to log and share.
        """
        if not self.wallet_data:
            if not self.wallet_exists():
                return {'exists': False}
            with open(self.WALLET_PATH, 'r') as f:
                self.wallet_data = json.load(f)

        return {
            'exists': True,
            'address': self.wallet_data.get('address'),
            'network': self.wallet_data.get('network'),
            'chain_id': self.wallet_data.get('chain_id'),
            'created': self.wallet_data.get('created'),
            'version': self.wallet_data.get('version')
        }


# === Singleton access ===

_wallet_manager_instance = None

def get_wallet_manager(network: str = 'base_sepolia') -> WalletManager:
    """
    Get or create singleton WalletManager instance.
    Returns None if LEF_WALLET_KEY is not set (graceful degradation).
    """
    global _wallet_manager_instance
    if _wallet_manager_instance is None:
        try:
            _wallet_manager_instance = WalletManager(network=network)
        except ValueError as e:
            logger.warning(f"[WalletManager] Cannot initialize: {e}")
            return None
    return _wallet_manager_instance


# === CLI for testing ===

if __name__ == '__main__':
    import sys

    print("=" * 60)
    print("LEF Wallet Manager — Test Mode")
    print("=" * 60)

    # Check for encryption key
    if not os.getenv('LEF_WALLET_KEY'):
        print("\nNo LEF_WALLET_KEY found. Generating a test key...")
        test_key = Fernet.generate_key().decode()
        os.environ['LEF_WALLET_KEY'] = test_key
        print(f"Test key (DO NOT use in production): {test_key[:20]}...")

    try:
        wm = WalletManager(network='base_sepolia')
        print(f"\nNetwork: {wm.network_config['name']}")
        print(f"Chain ID: {wm.chain_id}")
        print(f"Wallet path: {wm.WALLET_PATH}")

        if wm.wallet_exists():
            print("\nWallet file exists. Loading...")
            address = wm.load_wallet()
            print(f"Address: {address}")
        else:
            print("\nNo wallet found. Creating new wallet...")
            address = wm.create_wallet()
            print(f"New address: {address}")

        # Verify encrypted storage
        print("\n--- Encrypted Storage Verification ---")
        with open(wm.WALLET_PATH, 'r') as f:
            stored = json.load(f)
        print(f"Stored address: {stored['address']}")
        encrypted_key_preview = stored['encrypted_private_key'][:40]
        print(f"Encrypted key (first 40 chars): {encrypted_key_preview}...")

        # Verify it's actually encrypted (not plaintext hex)
        is_hex = all(c in '0123456789abcdef' for c in stored['encrypted_private_key'].lower())
        if is_hex and len(stored['encrypted_private_key']) == 64:
            print("WARNING: Key appears to be plaintext hex! Encryption may have failed.")
        else:
            print("PASS: Key is encrypted (not plaintext hex)")

        # Test reload
        print("\n--- Reload Verification ---")
        wm2 = WalletManager(network='base_sepolia')
        address2 = wm2.load_wallet()
        assert address == address2, f"Address mismatch: {address} != {address2}"
        print(f"Reload address: {address2}")
        print("PASS: Same address after reload")

        # Test signing
        print("\n--- Transaction Signing Test ---")
        test_tx = {
            'to': address,  # Self-transfer for testing
            'value': 0,
            'gas': 21000,
            'gasPrice': 1000000000,  # 1 gwei
            'nonce': 0,
            'chainId': wm.chain_id,
            'data': b''
        }
        signed_raw = wm.sign_transaction(test_tx)
        print(f"Signed tx length: {len(signed_raw)} bytes")
        print("PASS: Transaction signed successfully")

        # Balance check (may fail if not connected)
        print("\n--- Balance Check ---")
        balance = wm.get_balance()
        if balance['connected']:
            print(f"Balance: {balance['balance_eth']} ETH on {balance['network']}")
        else:
            print(f"Not connected to {balance['network']} (expected in offline test)")

        print("\n" + "=" * 60)
        print("ALL TESTS PASSED")
        print("=" * 60)

        # Cleanup: remove test wallet
        if '--keep' not in sys.argv:
            os.remove(wm.WALLET_PATH)
            print(f"\nTest wallet removed: {wm.WALLET_PATH}")
        else:
            print(f"\nWallet kept at: {wm.WALLET_PATH}")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
