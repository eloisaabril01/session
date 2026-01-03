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

    def _get_msg_content(self, msg):
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
        return re.sub(r'\s+', ' ', content)

    def get_otp(self, target_alias, timeout=120):
        logger.info(f"Searching for OTP for {target_alias} in Gmail...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self.mail.select("inbox")
                # Search all messages in inbox (Instagram search might be filtered out by some forwarders)
                status, messages = self.mail.search(None, 'ALL')
                if status == "OK":
                    # Check the last 10 messages for speed and relevance
                    msg_nums = messages[0].split()
                    for num in reversed(msg_nums[-10:]):
                        status, data = self.mail.fetch(num, "(RFC822)")
                        if status == "OK":
                            msg = email.message_from_bytes(data[0][1])
                            subject = str(msg.get("Subject", ""))
                            to_header = str(msg.get("To", ""))
                            from_header = str(msg.get("From", ""))
                            content = self._get_msg_content(msg)
                            
                            logger.debug(f"Checking email from {from_header}: {subject}")
                            
                            # Match if the target alias is mentioned anywhere (Subject, To, or Body)
                            if (target_alias.lower() in to_header.lower() or 
                                target_alias.lower() in content.lower() or 
                                target_alias.lower() in subject.lower()):
                                
                                # Extract 6-digit codes from body or subject
                                codes = re.findall(r"\b(\d{6})\b", content)
                                if not codes:
                                    codes = re.findall(r"\b(\d{6})\b", subject)
                                    
                                if codes:
                                    # Ignore any numbers that are part of the alias itself
                                    alias_num_part = "".join(filter(str.isdigit, target_alias.split('@')[0]))
                                    valid_codes = [c for c in codes if c != alias_num_part]
                                    
                                    if valid_codes:
                                        extracted_otp = valid_codes[0]
                                        logger.info(f"Found OTP {extracted_otp} for {target_alias}")
                                        return extracted_otp
                else:
                    logger.debug("No emails found in inbox.")
            except Exception as e:
                logger.error(f"Error checking Gmail: {e}")
            time.sleep(10)
        logger.warning(f"Timeout reached. No OTP found for {target_alias}")
        return None

    def disconnect(self):
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except:
                pass
