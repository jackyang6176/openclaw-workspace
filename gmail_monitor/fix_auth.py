#!/usr/bin/env python3

import os
import pickle
import sys
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save the credentials for the next run
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)
                print("Token refreshed successfully!")
                return True
            except Exception as e:
                print(f"Error refreshing token: {e}")
                # If refresh fails, we need to re-authenticate
        
        # Delete the old token
        if os.path.exists('token.pickle'):
            os.remove('token.pickle')
            
        # Run the authentication flow
        if not os.path.exists('credentials.json'):
            print("Error: credentials.json not found!")
            return False
            
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
        print("New token obtained successfully!")
        return True
    
    print("Credentials are valid!")
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)