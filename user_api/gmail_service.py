from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
import os
import pickle

class GmailService:
    def __init__(self, sender_email: str):
        self.sender_email = sender_email  # 指定发件人邮箱
        base_dir = Path(__file__).parent.parent 
        self.secrets_path = base_dir / "config" / "secrets" / "client_secret_771384916731-rlvt5800trutb500j7dvphtp9pp5qa65.apps.googleusercontent.com.json"
        self.token_path = base_dir / "config" / "secrets" / "token.pickle"
        self.creds = self._get_credentials()
        self.service = build('gmail', 'v1', credentials=self.creds)
    
    def _get_credentials(self):
        creds = None
        # 尝试从文件加载凭据
        if self.token_path.exists():
            with open(self.token_path, 'rb') as token:
                creds = pickle.load(token)
                
        # 如果没有凭据或已过期
        if not creds or not creds.valid:
            if False:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(self.secrets_path),  # 使用实际文件名
                    ['https://www.googleapis.com/auth/gmail.send']
                )
                creds = flow.run_local_server(port=0)
            # 保存凭据
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        
        return creds

    async def send_verification_email(self, to_email: str, code: str):
        # 创建 HTML 邮件内容
        html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="color: #333; font-size: 28px;">Verification Code</h1>
                </div>
                
                <div style="padding: 20px; background-color: #fff; border-radius: 5px;">
                    <p style="color: #333; font-size: 16px;">Hi there,</p>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.5;">Please enter this code to verify your email:</p>
                    
                    <div style="background-color: #f5f5f5; padding: 20px; border-radius: 5px; margin: 25px 0; text-align: center;">
                        <h2 style="color: #333; margin: 0; font-size: 32px; letter-spacing: 2px;">{code}</h2>
                    </div>
                    
                    <p style="color: #333; font-size: 16px; line-height: 1.5;">If you were not trying to sign in, please ignore this email.</p>
                    
                    <p style="color: #333; margin-top: 30px; font-size: 16px;">
                        Best,<br>
                        <span style="font-size: 16px; font-weight: 500;">CarQuest Team</span>
                    </p>
                </div>
                
                <div style="text-align: center; margin-top: 20px; color: #666; font-size: 14px;">
                    <p>If you have any questions please contact us through our help center</p>
                </div>
            </div>
            """

        message = MIMEMultipart('alternative')
        message['from'] = self.sender_email  # Add this line
        message['to'] = to_email
        message['subject'] = 'Verification Code'
        
        # 添加纯文本和 HTML 版本
        text_part = MIMEText(f'Your verification code is: {code}', 'plain')
        html_part = MIMEText(html_content, 'html')
        
        message.attach(text_part)
        message.attach(html_part)

        try:
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            self.service.users().messages().send(
                userId='me',
                body={'raw': encoded_message}
            ).execute()
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False