from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import pytz
from typing import Dict, Any
import yaml  # pyyaml
import os
from entrypoint import load_gin

load_gin("ingest-kafka", test=False)

from greenflow.analysis.tiny import get_experiments

def load_tinydb_data(file_path: str) -> Dict[str, Any]:
    return get_experiments()
    # """Load TinyDB YAML data from file"""
    # with open(file_path, 'r') as f:
    #     data = yaml.safe_load(f)
    # return data.get('_default', {})

def transform_experiment(exp_id: str, exp_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform TinyDB experiment entry to MongoDB schema"""
    
    transformed = {
        'exp_name': exp_data['exp_name'],
        'experiment_description': exp_data['experiment_description'],
        'started_ts': exp_data['started_ts'],
        'stopped_ts': exp_data['stopped_ts'],
        'experiment_metadata': {
            'factors': exp_data['experiment_metadata']['factors'],
            'results': exp_data['experiment_metadata'].get('results', {}),
            'deployment_metadata': exp_data['experiment_metadata'].get('deployment_metadata', {}),
        }
    }
    
    # Optional fields
    optional_fields = ['dashboard_url', 'explore_url']
    for field in optional_fields:
        if field in exp_data['experiment_metadata']:
            transformed['experiment_metadata'][field] = exp_data['experiment_metadata'][field]
    
    # Add numeric experiment ID from TinyDB as reference
    transformed['legacy_ids'] = [exp_id]
    
    return transformed

def migrate(source_file: str, mongodb_uri: str = None, db_name: str = "greenflow", collection_name: str = "experiments_test"):
    """Main migration function"""
    # Connect to MongoDB
    client = MongoClient(mongodb_uri or os.getenv("MONGO_URL", "mongodb://localhost:27017/"))
    db = client[db_name]
    collection = db[collection_name]
    
    # Load TinyDB data
    experiments = load_tinydb_data(source_file)
    
    # Process and migrate each experiment
    for exp_id, exp_data in experiments.items():
        mongo_doc = transform_experiment(exp_id, exp_data)
        result = collection.insert_one(mongo_doc)
        print(f"Migrated experiment {exp_id} to MongoDB ID: {result.inserted_id}")
    
    # Create indexes
    collection.create_index([("started_ts", 1)])
    collection.create_index([("exp_name", 1)])
    collection.create_index([("experiment_metadata.factors.exp_params", 1)])
    
    print(f"Migration complete. {len(experiments)} experiments migrated.")

# Example usage
if __name__ == "__main__":
    migrate(
        source_file="storage/experiment_history.yaml",
        mongodb_uri="mongodb://localhost:27017/"
    )
