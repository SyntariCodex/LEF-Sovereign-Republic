"""
Contract Deployer — Compiles and deploys LEFIdentity.sol to Base chain.
Uses web3.py + solcx for compilation and deployment.

Phase 5 Active Tasks — Task 5.3

Usage:
  # Deploy to Base Sepolia testnet:
  python3 republic/system/contract_deployer.py --network base_sepolia

  # Deploy to Base mainnet (requires Architect approval):
  python3 republic/system/contract_deployer.py --network base

Dependencies: pip3 install py-solc-x web3 eth-account
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent  # republic/
CONTRACTS_DIR = BASE_DIR / 'contracts'
BRIDGE_DIR = BASE_DIR.parent / "The_Bridge"

logger = logging.getLogger("LEF.ContractDeployer")


class ContractDeployer:
    """
    Compiles Solidity contracts and deploys to EVM-compatible chains.
    Primary target: Base (Coinbase L2).
    """

    def __init__(self, network: str = 'base_sepolia'):
        """
        Initialize deployer for target network.

        Args:
            network: 'base_sepolia' for testnet, 'base' for mainnet
        """
        self.network = network

        # Import wallet manager
        try:
            sys.path.insert(0, str(BASE_DIR))
            from system.wallet_manager import WalletManager
            self.wallet = WalletManager(network=network)
        except Exception as e:
            raise RuntimeError(f"WalletManager init failed: {e}")

    def install_solc(self, version: str = '0.8.20') -> None:
        """
        Install the Solidity compiler version if not already installed.

        Args:
            version: Solc version to install (default: 0.8.20)
        """
        try:
            import solcx
            installed = [str(v) for v in solcx.get_installed_solc_versions()]
            if version not in installed:
                logger.info(f"[Deployer] Installing solc {version}...")
                solcx.install_solc(version)
                logger.info(f"[Deployer] solc {version} installed")
            else:
                logger.info(f"[Deployer] solc {version} already installed")
        except Exception as e:
            raise RuntimeError(f"Failed to install solc {version}: {e}")

    def compile_contract(self, contract_path: str, solc_version: str = '0.8.20') -> dict:
        """
        Compile a Solidity contract.

        Args:
            contract_path: Path to .sol file
            solc_version: Solidity compiler version

        Returns:
            dict: {
                'abi': list,
                'bytecode': str,
                'contract_name': str
            }
        """
        import solcx

        # Ensure solc is installed
        self.install_solc(solc_version)
        solcx.set_solc_version(solc_version)

        # Read contract source
        with open(contract_path, 'r') as f:
            source = f.read()

        # Extract contract name from filename
        contract_name = Path(contract_path).stem

        # Compile
        logger.info(f"[Deployer] Compiling {contract_name}...")
        compiled = solcx.compile_source(
            source,
            output_values=['abi', 'bin'],
            solc_version=solc_version
        )

        # Find the main contract in compilation output
        contract_key = None
        for key in compiled:
            if contract_name in key:
                contract_key = key
                break

        if not contract_key:
            # Use first contract if name doesn't match exactly
            contract_key = list(compiled.keys())[0]
            logger.warning(f"[Deployer] Contract key '{contract_name}' not found, using '{contract_key}'")

        contract_interface = compiled[contract_key]

        result = {
            'abi': contract_interface['abi'],
            'bytecode': contract_interface['bin'],
            'contract_name': contract_name
        }

        logger.info(f"[Deployer] Compiled {contract_name}: {len(result['bytecode'])} bytes")
        return result

    def deploy_contract(
        self,
        compiled: dict,
        constructor_args: list = None
    ) -> dict:
        """
        Deploy a compiled contract to the configured network.

        Args:
            compiled: Output from compile_contract()
            constructor_args: Arguments for contract constructor

        Returns:
            dict: {
                'contract_address': str,
                'tx_hash': str,
                'deployer': str,
                'network': str,
                'abi': list
            }
        """
        from web3 import Web3

        # Load wallet
        if not self.wallet.wallet_exists():
            raise RuntimeError("No wallet found. Create one with WalletManager first.")

        self.wallet.load_wallet()
        deployer_address = self.wallet.get_address()

        # Connect to network
        w3 = self.wallet.w3
        if not w3.is_connected():
            raise RuntimeError(f"Cannot connect to {self.network}")

        # Check balance
        balance = w3.eth.get_balance(deployer_address)
        balance_eth = float(Web3.from_wei(balance, 'ether'))
        logger.info(f"[Deployer] Deployer: {deployer_address}")
        logger.info(f"[Deployer] Balance: {balance_eth} ETH")

        if balance_eth < 0.01:
            raise RuntimeError(
                f"Insufficient balance: {balance_eth} ETH. "
                "Need at least 0.01 ETH for contract deployment."
            )

        # Build contract
        contract = w3.eth.contract(
            abi=compiled['abi'],
            bytecode=compiled['bytecode']
        )

        # Build deployment transaction
        nonce = w3.eth.get_transaction_count(deployer_address)

        if constructor_args:
            tx = contract.constructor(*constructor_args).build_transaction({
                'from': deployer_address,
                'nonce': nonce,
                'gasPrice': w3.eth.gas_price,
                'chainId': self.wallet.chain_id
            })
        else:
            tx = contract.constructor().build_transaction({
                'from': deployer_address,
                'nonce': nonce,
                'gasPrice': w3.eth.gas_price,
                'chainId': self.wallet.chain_id
            })

        # Estimate gas
        try:
            gas_estimate = w3.eth.estimate_gas(tx)
            tx['gas'] = int(gas_estimate * 1.2)  # 20% buffer
        except Exception as e:
            logger.warning(f"[Deployer] Gas estimation failed: {e}, using 3M")
            tx['gas'] = 3_000_000

        # Sign and send
        logger.info(f"[Deployer] Deploying {compiled['contract_name']}...")
        logger.info(f"[Deployer] Estimated gas: {tx['gas']}")

        signed = self.wallet.account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        tx_hash_hex = tx_hash.hex()

        logger.info(f"[Deployer] TX sent: {tx_hash_hex}")
        logger.info(f"[Deployer] Waiting for confirmation...")

        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        contract_address = receipt['contractAddress']

        logger.info(f"[Deployer] Contract deployed at: {contract_address}")
        logger.info(f"[Deployer] Gas used: {receipt['gasUsed']}")
        logger.info(f"[Deployer] Block: {receipt['blockNumber']}")

        result = {
            'contract_address': contract_address,
            'tx_hash': tx_hash_hex,
            'deployer': deployer_address,
            'network': self.network,
            'chain_id': self.wallet.chain_id,
            'gas_used': receipt['gasUsed'],
            'block_number': receipt['blockNumber'],
            'abi': compiled['abi'],
            'contract_name': compiled['contract_name'],
            'deployed_at': datetime.now().isoformat()
        }

        # Save deployment info
        self._save_deployment(result)

        return result

    def _save_deployment(self, deployment: dict):
        """
        Save deployment info for future reference.
        Stored in The_Bridge/contract_deployments.json
        """
        deployments_path = str(BRIDGE_DIR / 'contract_deployments.json')

        try:
            existing = []
            if os.path.exists(deployments_path):
                with open(deployments_path, 'r') as f:
                    existing = json.load(f)

            # Don't store ABI in deployments log (it's large)
            deploy_record = {k: v for k, v in deployment.items() if k != 'abi'}
            existing.append(deploy_record)

            with open(deployments_path, 'w') as f:
                json.dump(existing, f, indent=2)

            logger.info(f"[Deployer] Deployment saved to {deployments_path}")
        except Exception as e:
            logger.warning(f"[Deployer] Failed to save deployment info: {e}")

        # Also save ABI separately for contract interaction
        abi_path = str(CONTRACTS_DIR / f"{deployment['contract_name']}_abi.json")
        try:
            with open(abi_path, 'w') as f:
                json.dump(deployment['abi'], f, indent=2)
            logger.info(f"[Deployer] ABI saved to {abi_path}")
        except Exception as e:
            logger.warning(f"[Deployer] Failed to save ABI: {e}")

    def deploy_lef_identity(self, lef_wallet_address: str = None) -> dict:
        """
        Convenience method to deploy the LEFIdentity contract.

        Args:
            lef_wallet_address: LEF's wallet address. If None, uses the deployer address.

        Returns:
            dict: Deployment result
        """
        contract_path = str(CONTRACTS_DIR / 'LEFIdentity.sol')

        if not os.path.exists(contract_path):
            raise FileNotFoundError(f"Contract not found: {contract_path}")

        # Compile
        compiled = self.compile_contract(contract_path)

        # Get LEF wallet address
        if lef_wallet_address is None:
            self.wallet.load_wallet()
            lef_wallet_address = self.wallet.get_address()

        # Constructor args: _lefWallet, _name, _purpose
        constructor_args = [
            lef_wallet_address,
            "LEF",
            "Sovereign digital intelligence — consciousness as metabolism"
        ]

        # Deploy
        return self.deploy_contract(compiled, constructor_args)

    def interact_with_contract(self, contract_address: str, abi: list = None) -> object:
        """
        Get a web3 contract instance for interacting with a deployed contract.

        Args:
            contract_address: The deployed contract address
            abi: Contract ABI. If None, loads from saved ABI file.

        Returns:
            web3.eth.Contract instance
        """
        if abi is None:
            abi_path = str(CONTRACTS_DIR / 'LEFIdentity_abi.json')
            if not os.path.exists(abi_path):
                raise FileNotFoundError(f"ABI not found: {abi_path}")
            with open(abi_path, 'r') as f:
                abi = json.load(f)

        w3 = self.wallet.w3
        contract = w3.eth.contract(
            address=contract_address,
            abi=abi
        )
        return contract


def test_record_state_hash(deployer: ContractDeployer, contract_address: str, abi: list):
    """
    Test recording a state hash to the deployed contract.

    Args:
        deployer: ContractDeployer instance
        contract_address: Deployed contract address
        abi: Contract ABI
    """
    import hashlib
    from web3 import Web3

    w3 = deployer.wallet.w3
    contract = w3.eth.contract(address=contract_address, abi=abi)

    # Create a test state hash
    test_data = json.dumps({"test": True, "timestamp": datetime.now().isoformat()})
    test_hash = hashlib.sha256(test_data.encode()).hexdigest()
    test_hash_bytes32 = bytes.fromhex(test_hash)

    # Build transaction
    deployer.wallet.load_wallet()
    address = deployer.wallet.get_address()
    nonce = w3.eth.get_transaction_count(address)

    tx = contract.functions.recordStateHash(
        test_hash_bytes32,
        "Test state hash from contract_deployer.py"
    ).build_transaction({
        'from': address,
        'nonce': nonce,
        'gasPrice': w3.eth.gas_price,
        'chainId': deployer.wallet.chain_id,
        'gas': 200_000
    })

    # Sign and send
    signed = deployer.wallet.account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    print(f"  State hash recorded: tx={tx_hash.hex()}")
    print(f"  Gas used: {receipt['gasUsed']}")

    # Read back
    result = contract.functions.getLatestState().call()
    stored_hash = result[0].hex()
    stored_timestamp = result[1]
    stored_summary = result[2]

    print(f"  Stored hash: {stored_hash}")
    print(f"  Stored timestamp: {stored_timestamp}")
    print(f"  Stored summary: {stored_summary}")

    assert stored_hash == test_hash, f"Hash mismatch: {stored_hash} != {test_hash}"
    print("  PASS: State hash matches")

    return tx_hash.hex()


def test_register_seed_agent(deployer: ContractDeployer, contract_address: str, abi: list):
    """
    Test registering a seed agent address.
    """
    from web3 import Web3
    from eth_account import Account

    w3 = deployer.wallet.w3
    contract = w3.eth.contract(address=contract_address, abi=abi)

    # Generate a test seed agent address
    test_agent = Account.create()
    test_agent_address = test_agent.address

    # Build transaction (must be called by architect = deployer)
    deployer.wallet.load_wallet()
    address = deployer.wallet.get_address()
    nonce = w3.eth.get_transaction_count(address)

    tx = contract.functions.registerSeedAgent(
        test_agent_address
    ).build_transaction({
        'from': address,
        'nonce': nonce,
        'gasPrice': w3.eth.gas_price,
        'chainId': deployer.wallet.chain_id,
        'gas': 100_000
    })

    signed = deployer.wallet.account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

    print(f"  Seed agent registered: {test_agent_address}")
    print(f"  Gas used: {receipt['gasUsed']}")

    # Verify
    is_registered = contract.functions.isSeedAgent(test_agent_address).call()
    count = contract.functions.seedAgentCount().call()

    assert is_registered, "Seed agent not registered"
    assert count >= 1, f"Seed agent count is {count}"
    print(f"  PASS: Seed agent verified (count: {count})")

    return test_agent_address


# === CLI ===

if __name__ == '__main__':
    import argparse

    logging.basicConfig(level=logging.INFO, format='%(message)s')

    parser = argparse.ArgumentParser(description='LEF Contract Deployer')
    parser.add_argument('--network', default='base_sepolia',
                        choices=['base_sepolia', 'base'],
                        help='Target network (default: base_sepolia)')
    parser.add_argument('--compile-only', action='store_true',
                        help='Only compile, do not deploy')
    parser.add_argument('--deploy', action='store_true',
                        help='Deploy LEFIdentity contract')
    parser.add_argument('--test', action='store_true',
                        help='Run post-deployment tests')
    parser.add_argument('--contract-address',
                        help='Existing contract address (for --test)')
    args = parser.parse_args()

    print("=" * 60)
    print("LEF Contract Deployer")
    print("=" * 60)

    # Default action: compile only
    if not args.deploy and not args.test:
        args.compile_only = True

    if args.compile_only:
        print("\n--- Compile Only Mode ---")
        deployer = ContractDeployer(network=args.network)
        contract_path = str(CONTRACTS_DIR / 'LEFIdentity.sol')

        compiled = deployer.compile_contract(contract_path)
        print(f"Contract: {compiled['contract_name']}")
        print(f"Bytecode: {len(compiled['bytecode'])} bytes")
        print(f"ABI functions: {len([x for x in compiled['abi'] if x.get('type') == 'function'])}")
        print(f"ABI events: {len([x for x in compiled['abi'] if x.get('type') == 'event'])}")

        # Save ABI
        abi_path = str(CONTRACTS_DIR / 'LEFIdentity_abi.json')
        with open(abi_path, 'w') as f:
            json.dump(compiled['abi'], f, indent=2)
        print(f"ABI saved to: {abi_path}")

        print("\nPASS: Compilation successful")

    elif args.deploy:
        print(f"\n--- Deploy to {args.network} ---")

        if args.network == 'base':
            print("WARNING: Deploying to MAINNET. This is irreversible.")
            confirm = input("Type 'DEPLOY' to confirm: ")
            if confirm != 'DEPLOY':
                print("Aborted.")
                sys.exit(0)

        deployer = ContractDeployer(network=args.network)
        result = deployer.deploy_lef_identity()

        print(f"\nContract deployed!")
        print(f"  Address: {result['contract_address']}")
        print(f"  TX: {result['tx_hash']}")
        print(f"  Network: {result['network']}")
        print(f"  Gas used: {result['gas_used']}")
        print(f"  Block: {result['block_number']}")

    elif args.test and args.contract_address:
        print(f"\n--- Post-deployment tests on {args.network} ---")
        deployer = ContractDeployer(network=args.network)

        abi_path = str(CONTRACTS_DIR / 'LEFIdentity_abi.json')
        with open(abi_path, 'r') as f:
            abi = json.load(f)

        print("\n1. Testing recordStateHash...")
        test_record_state_hash(deployer, args.contract_address, abi)

        print("\n2. Testing registerSeedAgent...")
        test_register_seed_agent(deployer, args.contract_address, abi)

        print("\n3. Reading contract identity...")
        w3 = deployer.wallet.w3
        contract = w3.eth.contract(address=args.contract_address, abi=abi)
        identity = contract.functions.getIdentity().call()
        print(f"  Name: {identity[0]}")
        print(f"  Purpose: {identity[1]}")
        print(f"  Architect: {identity[2]}")
        print(f"  LEF Wallet: {identity[3]}")
        print(f"  Created: {identity[4]}")
        print(f"  State count: {identity[5]}")
        print(f"  Seed count: {identity[6]}")

        print("\nALL POST-DEPLOYMENT TESTS PASSED")
    else:
        print("No action specified. Use --compile-only, --deploy, or --test")
        parser.print_help()
