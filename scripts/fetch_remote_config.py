#!/usr/bin/env python
import requests
import json
import sys
import os
import argparse
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_config(url: str, output_file: str = None):
    """
    Fetch configuration from a remote URL and output it as JSON
    
    Args:
        url: URL to fetch configuration from
        output_file: Optional file path to save the configuration to
    """
    try:
        logger.info(f"Fetching configuration from {url}")
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        if 'propertySources' not in data:
            logger.warning("Response does not appear to be a Spring Cloud Config format")
            result = data
        else:
            if len(data['propertySources']) < 1:
                logger.warning(f"No configuration data found at {url}")
                return {}
                
            config = {}
            if len(data['propertySources']) > 1:
                # Load default data first
                config = data['propertySources'][1].get('source', {})
            
            # Override with specific config
            config.update(data['propertySources'][0].get('source', {}))
            
            # Convert flat dot notation to nested JSON
            result = {}
            for key, value in config.items():
                parts = key.split('.')
                current = result
                
                # Navigate to the right level
                for i, part in enumerate(parts):
                    if i == len(parts) - 1:
                        # Last part is the actual key
                        current[part] = value
                    else:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
        
        # Output the result
        json_data = json.dumps(result, indent=2)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(json_data)
            logger.info(f"Configuration saved to {output_file}")
        else:
            print(json_data)
            
        return result
    except Exception as e:
        logger.error(f"Error fetching configuration: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch configuration from a remote URL")
    parser.add_argument("url", help="URL to fetch configuration from")
    parser.add_argument("-o", "--output", help="File to save configuration to")
    args = parser.parse_args()
    
    fetch_config(args.url, args.output)