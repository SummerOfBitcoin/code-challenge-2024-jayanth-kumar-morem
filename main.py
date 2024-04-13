import hashlib
import json
import os
from dataclasses import dataclass, field

@dataclass
class Transaction:
    json_data: dict
    utxo_set: dict
    
    @property
    def txid(self):
        return self.json_data["vin"][0]["txid"]
    
    def is_valid(self):
        # Advanced validation checks
        if "version" not in self.json_data or self.json_data["version"] not in [1, 2]:
            return False
        if "locktime" not in self.json_data or not (self.json_data["locktime"] == 0 or self.json_data["locktime"] > 0):
            return False
        if not self.json_data["vin"] or not self.json_data["vout"]:
            return False
        if len(json.dumps(self.json_data).encode('utf-8')) > 100000:
            return False
        if any(vin["txid"] + str(vin["vout"]) in self.utxo_set for vin in self.json_data["vin"]):
            return False  # Checks for duplicate inputs within UTXO
        if any(vout["value"] < 0 for vout in self.json_data["vout"]):
            return False
        if sum(vin["prevout"]["value"] for vin in self.json_data["vin"]) < sum(vout["value"] for vout in self.json_data["vout"]):
            return False
        
        # Placeholder for script validation and signature verification
        # Real implementation would require cryptographic validation of scripts and signatures

        # Coinbase transaction special rules
        is_coinbase = any(vin.get("is_coinbase", False) for vin in self.json_data["vin"])
        if is_coinbase:
            if len(self.json_data["vin"]) != 1 or "prevout" in self.json_data["vin"][0]:
                return False

        # Non-coinbase transactions must reference existing UTXOs
        # if not is_coinbase:
        #     for vin in self.json_data["vin"]:
        #         if vin["txid"] + str(vin["vout"]) not in self.utxo_set:
        #             return False

        # Witness data check (for SegWit transactions)
        if "witness" in self.json_data:
            if not self.validate_witness_data():
                return False

        return True

    def validate_witness_data(self):
        # Placeholder for real witness data validation logic
        return True

@dataclass
class Block:
    transactions: list
    previous_hash: str
    nonce: int = 0
    hash: str = ""

    def calculate_hash(self):
        sha = hashlib.sha256()
        sha.update(f"{self.previous_hash}{self.nonce}{self.merkle_root()}".encode())
        return sha.hexdigest()

    def merkle_root(self):
        txid_string = ''.join(sorted(tx.txid for tx in self.transactions))
        return hashlib.sha256(txid_string.encode()).hexdigest()

    def mine(self, difficulty):
        assert len(difficulty) == 64
        target = int(difficulty, 16)
        while True:
            self.hash = self.calculate_hash()
            if int(self.hash, 16) < target:
                break
            self.nonce += 1

@dataclass
class Blockchain:
    blocks: list = field(default_factory=list)

    def add_block(self, block):
        self.blocks.append(block)

class Miner:
    def __init__(self, mempool_path):
        self.mempool_path = mempool_path
        self.transactions = []
        self.blockchain = Blockchain()
        self.difficulty = "0000ffff00000000000000000000000000000000000000000000000000000000"
        self.utxo_set = {}  # This would ideally be populated from blockchain data
    
    def load_transactions(self):
        for filename in os.listdir(self.mempool_path):
            with open(os.path.join(self.mempool_path, filename), 'r') as file:
                data = json.load(file)
                transaction = Transaction(data, self.utxo_set)
                if transaction.is_valid():
                    self.transactions.append(transaction)
                    # for vin in data["vin"]:  # Update UTXO set
                    #     self.utxo_set.pop(vin["txid"] + str(vin["vout"]), None)
                    # for index, vout in enumerate(data["vout"]):
                    #     self.utxo_set[data["txid"] + str(index)] = vout["value"]

    def select_transactions_for_block(self):
        return self.transactions[:10]

    def mine_block(self):
        previous_hash = '0' * 64 if not self.blockchain.blocks else self.blockchain.blocks[-1].hash
        transactions = self.select_transactions_for_block()
        new_block = Block(transactions, previous_hash)
        new_block.mine(self.difficulty)
        self.blockchain.add_block(new_block)
        return new_block

def main():
    miner = Miner('./mempool/')
    miner.load_transactions()
    new_block = miner.mine_block()

    with open('output.txt', 'w') as f:
        f.write(f"{new_block.hash}\n")
        f.write(f"{new_block.nonce}\n")
        for tx in new_block.transactions:
            f.write(f"{tx.txid}\n")

if __name__ == "__main__":
    main()
