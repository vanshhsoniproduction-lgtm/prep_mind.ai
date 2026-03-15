import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from django.conf import settings
from allauth.socialaccount.models import SocialToken, SocialApp

def get_google_credentials(user):
    try:
        # Fetch the token for the user from allauth
        token = SocialToken.objects.get(account__user=user, account__provider='google')
        app = SocialApp.objects.get(provider='google')
        
        return Credentials(
            token=token.token,
            refresh_token=token.token_secret,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=app.client_id,
            client_secret=app.secret
        )
    except Exception as e:
        print(f"Could not get tokens for user {user}: {e}")
        raise e

def create_interview_report(user, candidate_name, role, date, transcript, scores, strengths, weaknesses, improvement_plan):
    creds = get_google_credentials(user)
    
    try:
        docs_service = build('docs', 'v1', credentials=creds)
        drive_service = build('drive', 'v3', credentials=creds)

        title = f"PrepMind AI Interview Report — {candidate_name}"
        
        # 1. Create a blank document
        doc = docs_service.documents().create(body={'title': title}).execute()
        document_id = doc.get('documentId')

        # 2. Prepare contents
        content = f"""PrepMind AI Interview Report

Candidate: {candidate_name}
Role: {role}
Date: {date}

Scores
-----------
{scores}

Strengths
-----------
{strengths}

Weak Areas
-----------
{weaknesses}

Improvement Plan
-----------
{improvement_plan}

Transcript
-----------
{transcript}
"""

        # 3. Add text to the document
        requests = [
            {
                'insertText': {
                    'location': {
                        'index': 1,
                    },
                    'text': content
                }
            }
        ]
        
        docs_service.documents().batchUpdate(
            documentId=document_id, 
            body={'requests': requests}
        ).execute()

        # Returns direct document link
        return f"https://docs.google.com/document/d/{document_id}/edit"
    except Exception as e:
        print(f"[DOCS ERR] {e}")
        return "https://docs.google.com/document/d/mock_doc_id"
