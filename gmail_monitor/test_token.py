#!/usr/bin/env python3
import pickle
import os

# Test if token.pickle is valid
token_path = 'token.pickle'

if os.path.exists(token_path):
    try:
        with open(token_path, 'rb') as token_file:
            token = pickle.load(token_file)
        print("SUCCESS: token.pickle is valid and can be loaded.")
        print(f"Token type: {type(token)}")
        # Check if it has the expected attributes for a Gmail API token
        if hasattr(token, 'access_token') and hasattr(token, 'refresh_token'):
            print("Token has required attributes for Gmail API authentication.")
        else:
            print("WARNING: Token may be missing required attributes.")
    except Exception as e:
        print(f"ERROR: Failed to load token.pickle - {e}")
else:
    print("ERROR: token.pickle file not found.")