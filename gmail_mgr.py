import imaplib
import email
import re
import time
import logging

logger = logging.getLogger(__name__)

class GmailManager:
    def __init__(self, email_address, app_password):
        self.email_address = email_address
        self.app_password = app_password
        self.mail = None

    def connect(self):
        try:
            self.mail = imaplib.IMAP4_SSL("imap.gmail.com")
            self.mail.login(self.email_address, self.app_password)
            return True
        except Exception as e:
            logger.error(f"Gmail login failed: {e}")
            return False

    def get_otp(self, target_alias, timeout=120):
        logger.info(f"Waiting for OTP for {target_alias}...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self.mail.select("inbox")
                # Search for emails from Instagram
                status, messages = self.mail.search(None, '(FROM "no-reply@mail.instagram.com")')
                if status == "OK":
                    # Iterate through messages in reverse to find the latest matching one
                    for num in reversed(messages[0].split()):
                        status, data = self.mail.fetch(num, "(RFC822)")
                        if status == "OK":
                            msg = email.message_from_bytes(data[0][1])
                            to_header = str(msg.get("To", ""))
                            # Use regex to find the alias in the To header
                            if target_alias.lower() in to_header.lower():
                                content = ""
                                if msg.is_multipart():
                                    for part in msg.walk():
                                        if part.get_content_type() == "text/plain":
                                            try:
                                                content += part.get_payload(decode=True).decode()
                                            except:
                                                pass
                                else:
                                    try:
                                        content = msg.get_payload(decode=True).decode()
                                    except:
                                        pass
                                
                                # Clean content of potential encoding artifacts or weird spacing
                                content = re.sub(r'\s+', ' ', content)
                                
                                # Use re.finditer to get all 6-digit numbers and filter out the alias
                                codes = re.findall(r"\b(\d{6})\b", content)
                                if codes:
                                    alias_part = target_alias.split('+')[1].split('@')[0] if '+' in target_alias else ""
                                    
                                    # Filter out the alias suffix and get the first remaining code
                                    valid_codes = [c for c in codes if c != alias_part]
                                    
                                    if valid_codes:
                                        extracted_otp = valid_codes[0]
                                        logger.info(f"Verified OTP {extracted_otp} for {target_alias} (ignored alias {alias_part})")
                                        return extracted_otp
                                    else:
                                        logger.info(f"All codes found {codes} matched alias {alias_part}, continuing search...")
            except Exception as e:
                logger.error(f"Error checking Gmail: {e}")
            time.sleep(10)
        return None

    def disconnect(self):
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except:
                pass
