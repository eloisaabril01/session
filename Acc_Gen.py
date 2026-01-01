"""
Instagram Account Creator
Author: @CoderNamaste
"""

import os
import random
import string
import time
import logging
from typing import Optional, Dict, Tuple, Any
from dataclasses import dataclass
from enum import Enum

import names
from curl_cffi import requests as curl_requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResponseStatus(Enum):
    """Enum for response status types"""
    SUCCESS = "ok"
    FAILURE = "fail"
    ACCOUNT_CREATED = "account_created"
    EMAIL_SENT = "email_sent"


@dataclass
class AccountCredentials:
    """Data class for storing account credentials"""
    username: str
    password: str
    email: str
    session_id: str
    csrf_token: str
    ds_user_id: str
    ig_did: str
    rur: str
    mid: str
    datr: str

    def __str__(self) -> str:
        return (
            f"Username: {self.username}\n"
            f"Password: {self.password}\n"
            f"Email: {self.email}\n"
            f"Session ID: {self.session_id}\n"
            f"CSRF Token: {self.csrf_token}\n"
            f"DS User ID: {self.ds_user_id}\n"
            f"IG DID: {self.ig_did}\n"
            f"RUR: {self.rur}\n"
            f"MID: {self.mid}\n"
            f"DATR: {self.datr}"
        )


class InstagramAccountCreator:
    """
    A class for automating Instagram account creation process.

    This class handles the complete flow of creating an Instagram account,
    including header generation, email verification, and account setup.
    """

    BASE_URL = "https://www.instagram.com"
    API_BASE_URL = f"{BASE_URL}/api/v1"

    def __init__(self, country: str = "US", language: str = "en", proxies: Optional[Dict] = None):
        """
        Initialize the Instagram Account Creator.

        Args:
            country: Country code (e.g., 'US', 'UK')
            language: Language code (e.g., 'en', 'es')
            proxies: Optional proxy configuration dictionary
        """
        self.country = country
        self.language = language
        self.proxies = proxies

        # Initialize session with Chrome impersonation
        self.session = curl_requests.Session()
        self.session.impersonate = 'chrome110'

        # Initialize headers
        self.headers = None
        self.user_agent = None

        logger.info(f"Initialized Instagram Account Creator for {country}-{language}")

    def _generate_user_agent(self) -> str:
        """
        Generate a random mobile user agent string.

        Returns:
            A randomized user agent string
        """
        android_version = random.randint(9, 13)
        device_code = ''.join(random.choices(string.ascii_uppercase, k=3))
        device_number = random.randint(111, 999)

        user_agent = (
            f'Mozilla/5.0 (Linux; Android {android_version}; {device_code}{device_number}) '
            f'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36'
        )

        return user_agent

    def _extract_value_from_html(self, html: str, start_marker: str, end_marker: str) -> Optional[str]:
        """
        Extract a value from HTML content between markers.

        Args:
            html: HTML content to parse
            start_marker: Starting marker string
            end_marker: Ending marker string

        Returns:
            Extracted value or None if not found
        """
        try:
            start_index = html.index(start_marker) + len(start_marker)
            end_index = html.index(end_marker, start_index)
            return html[start_index:end_index]
        except (ValueError, IndexError):
            return None

    def generate_headers(self) -> Dict[str, str]:
        """
        Generate necessary headers for Instagram API requests.

        Returns:
            Dictionary containing all required headers

        Raises:
            Exception: If header generation fails after multiple attempts
        """
        max_attempts = 3

        for attempt in range(max_attempts):
            try:
                # Randomized sleep between attempts to avoid detection
                if attempt > 0:
                    time.sleep(random.uniform(10, 20))
                
                logger.info(f"Generating headers (Attempt {attempt + 1}/{max_attempts})")

                # Generate user agent
                self.user_agent = self._generate_user_agent()
                
                # Randomized wait before first request
                time.sleep(random.uniform(2, 5))

                # Initial request to get cookies
                initial_response = self.session.get(
                    self.BASE_URL,
                    headers={'user-agent': self.user_agent},
                    proxies=self.proxies,
                    timeout=30
                )

                # Extract necessary cookies and values
                js_datr = initial_response.cookies.get('datr')
                csrf_token = initial_response.cookies.get('csrftoken')
                ig_did = initial_response.cookies.get('ig_did')

                # Extract MID from response text
                mid = self._extract_value_from_html(
                    initial_response.text,
                    '{"mid":{"value":"',
                    '",'
                )

                if not all([js_datr, csrf_token, ig_did, mid]):
                    raise ValueError("Failed to extract required values from initial response")

                # Build initial headers for second request
                headers_step1 = {
                    'authority': 'www.instagram.com',
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'accept-language': f'{self.language}-{self.country},en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
                    'cookie': f'dpr=3; csrftoken={csrf_token}; mid={mid}; ig_nrcb=1; ig_did={ig_did}; datr={js_datr}',
                    'sec-ch-prefers-color-scheme': 'light',
                    'sec-ch-ua': '"Chromium";v="111", "Not(A:Brand";v="8"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                    'sec-fetch-dest': 'document',
                    'sec-fetch-mode': 'navigate',
                    'sec-fetch-site': 'none',
                    'sec-fetch-user': '?1',
                    'upgrade-insecure-requests': '1',
                    'user-agent': self.user_agent,
                    'viewport-width': '980',
                }

                # Second request to get app ID and rollout hash
                secondary_response = self.session.get(
                    self.BASE_URL,
                    headers=headers_step1,
                    proxies=self.proxies,
                    timeout=30
                )

                # Extract app ID and rollout hash
                app_id = self._extract_value_from_html(
                    secondary_response.text,
                    'APP_ID":"',
                    '"'
                )

                rollout_hash = self._extract_value_from_html(
                    secondary_response.text,
                    'rollout_hash":"',
                    '"'
                )

                if not all([app_id, rollout_hash]):
                    raise ValueError("Failed to extract app ID or rollout hash")

                # Build final headers
                self.headers = {
                    'authority': 'www.instagram.com',
                    'accept': '*/*',
                    'accept-language': f'{self.language}-{self.country},en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
                    'content-type': 'application/x-www-form-urlencoded',
                    'cookie': f'dpr=3; csrftoken={csrf_token}; mid={mid}; ig_nrcb=1; ig_did={ig_did}; datr={js_datr}',
                    'origin': self.BASE_URL,
                    'referer': f'{self.BASE_URL}/accounts/signup/email/',
                    'sec-ch-prefers-color-scheme': 'light',
                    'sec-ch-ua': '"Chromium";v="111", "Not(A:Brand";v="8"',
                    'sec-ch-ua-mobile': '?1',
                    'sec-ch-ua-platform': '"Android"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': self.user_agent,
                    'viewport-width': '360',
                    'x-asbd-id': '198387',
                    'x-csrftoken': csrf_token,
                    'x-ig-app-id': app_id,
                    'x-ig-www-claim': '0',
                    'x-instagram-ajax': rollout_hash,
                    'x-requested-with': 'XMLHttpRequest',
                    'x-web-device-id': ig_did,
                }

                logger.info("Headers generated successfully")
                return self.headers

            except Exception as e:
                logger.error(f"Error generating headers (Attempt {attempt + 1}): {e}")
                if attempt == max_attempts - 1:
                    raise Exception(f"Failed to generate headers after {max_attempts} attempts") from e
                time.sleep(2)  # Wait before retry

    def get_username_suggestion(self, name: str, email: str) -> Optional[str]:
        """
        Get username suggestions from Instagram.

        Args:
            name: Base name for username generation
            email: Email address for the account

        Returns:
            A suggested username or None if failed
        """
        if not self.headers:
            raise ValueError("Headers not generated. Call generate_headers() first.")

        try:
            # Update headers with appropriate referer
            headers = self.headers.copy()
            headers['referer'] = f'{self.BASE_URL}/accounts/signup/birthday/'

            # Generate random suffix for name
            name_with_suffix = f"{name}{random.randint(1, 99)}"

            data = {
                'email': email,
                'name': name_with_suffix,
            }

            response = self.session.post(
                f'{self.API_BASE_URL}/web/accounts/username_suggestions/',
                headers=headers,
                data=data,
                proxies=self.proxies,
                timeout=30
            )

            response_json = response.json()

            if response_json.get('status') == ResponseStatus.SUCCESS.value:
                suggestions = response_json.get('suggestions', [])
                if suggestions:
                    username = random.choice(suggestions)
                    logger.info(f"Username suggestion obtained: {username}")
                    return username
            else:
                logger.error(f"Failed to get username suggestion: {response.text}")

        except Exception as e:
            logger.error(f"Error getting username suggestion: {e}")

        return None

    def send_verification_email(self, email: str) -> bool:
        """
        Send verification email to the provided address.

        Args:
            email: Email address to send verification to

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.headers:
            raise ValueError("Headers not generated. Call generate_headers() first.")

        try:
            device_id = self._extract_device_id_from_headers()

            data = {
                'device_id': device_id,
                'email': email,
            }

            response = self.session.post(
                f'{self.API_BASE_URL}/accounts/send_verify_email/',
                headers=self.headers,
                data=data,
                proxies=self.proxies,
                timeout=30
            )

            # Update cookies from response
            self.session.cookies.update(response.cookies)
            if 'csrftoken' in response.cookies:
                self.headers['x-csrftoken'] = response.cookies['csrftoken']
                # Also update cookie string in headers if necessary
                cookie_parts = {c.split('=')[0]: c.split('=')[1] for c in self.headers['cookie'].split('; ')}
                cookie_parts['csrftoken'] = response.cookies['csrftoken']
                self.headers['cookie'] = '; '.join([f"{k}={v}" for k, v in cookie_parts.items()])

            if f'"{ResponseStatus.EMAIL_SENT.value}":true' in response.text:
                logger.info(f"Verification email sent successfully to {email}")
                return True
            else:
                logger.error(f"Failed to send verification email: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending verification email: {e}")
            return False

    def validate_verification_code(self, email: str, code: str) -> Optional[str]:
        """
        Validate the verification code sent to email.

        Args:
            email: Email address
            code: Verification code received

        Returns:
            Signup code if validation successful, None otherwise
        """
        if not self.headers:
            raise ValueError("Headers not generated. Call generate_headers() first.")

        try:
            # Always use latest CSRF from session
            csrf_token = self.session.cookies.get('csrftoken') or self.headers.get('x-csrftoken')
            
            headers = self.headers.copy()
            headers['referer'] = f'{self.BASE_URL}/accounts/signup/emailConfirmation/'
            if csrf_token:
                headers['x-csrftoken'] = csrf_token
                # Ensure cookie string is updated
                cookie_parts = {c.split('=')[0]: c.split('=')[1] for c in headers['cookie'].split('; ')}
                cookie_parts['csrftoken'] = csrf_token
                headers['cookie'] = '; '.join([f"{k}={v}" for k, v in cookie_parts.items()])

            device_id = self._extract_device_id_from_headers()

            data = {
                'code': code,
                'device_id': device_id,
                'email': email,
            }

            response = self.session.post(
                f'{self.API_BASE_URL}/accounts/check_confirmation_code/',
                headers=headers,
                data=data,
                proxies=self.proxies,
                timeout=30
            )

            # Update cookies from response
            self.session.cookies.update(response.cookies)

            response_json = response.json()

            if response_json.get('status') == ResponseStatus.SUCCESS.value:
                signup_code = response_json.get('signup_code')
                logger.info("Verification code validated successfully")
                return signup_code
            else:
                logger.error(f"Failed to validate code: {response.text}")

        except Exception as e:
            logger.error(f"Error validating verification code: {e}")

        return None

    def _extract_device_id_from_headers(self) -> str:
        """Extract device ID (MID) from headers."""
        return self.headers['cookie'].split('mid=')[1].split(';')[0]

    def _generate_password(self, base_name: str) -> str:
        """
        Generate a secure password.

        Args:
            base_name: Base name to use in password

        Returns:
            Generated password
        """
        return f"{base_name.strip()}@{random.randint(111, 999)}"

    def _generate_birth_date(self) -> Tuple[int, int, int]:
        """
        Generate random birth date.

        Returns:
            Tuple of (month, day, year)
        """
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # Safe for all months
        year = random.randint(1990, 2001)
        return month, day, year

    def create_account(self, email: str, signup_code: str) -> Optional[AccountCredentials]:
        """
        Create Instagram account with provided email and signup code.

        Args:
            email: Email address for the account
            signup_code: Signup code from email verification

        Returns:
            AccountCredentials object if successful, None otherwise
        """
        if not self.headers:
            raise ValueError("Headers not generated. Call generate_headers() first.")

        try:
            # Generate account details
            first_name = names.get_first_name()
            username = self.get_username_suggestion(first_name, email)

            if not username:
                logger.error("Failed to get username suggestion")
                return None

            password = self._generate_password(first_name)
            month, day, year = self._generate_birth_date()

            # Update headers
            headers = self.headers.copy()
            headers['referer'] = f'{self.BASE_URL}/accounts/signup/username/'

            # Prepare account creation data
            data = {
                'enc_password': f'#PWD_INSTAGRAM_BROWSER:0:{round(time.time())}:{password}',
                'email': email,
                'username': username,
                'first_name': first_name,
                'month': month,
                'day': day,
                'year': year,
                'client_id': self._extract_device_id_from_headers(),
                'seamless_login_enabled': '1',
                'tos_version': 'row',
                'force_sign_up_code': signup_code,
            }

            logger.info(f"Creating account with username: {username}")

            # Send account creation request
            response = self.session.post(
                f'{self.API_BASE_URL}/web/accounts/web_create_ajax/',
                headers=headers,
                data=data,
                proxies=self.proxies,
                timeout=30
            )

            # Check if account was created successfully
            if f'"{ResponseStatus.ACCOUNT_CREATED.value}":true' in response.text:
                logger.info("Account created successfully!")

                # Extract cookies and create credentials object
                credentials = AccountCredentials(
                    username=username,
                    password=password,
                    email=email,
                    session_id=response.cookies.get('sessionid', ''),
                    csrf_token=response.cookies.get('csrftoken', ''),
                    ds_user_id=response.cookies.get('ds_user_id', ''),
                    ig_did=response.cookies.get('ig_did', ''),
                    rur=response.cookies.get('rur', ''),
                    mid=self._extract_device_id_from_headers(),
                    datr=self.headers['cookie'].split('datr=')[1]
                )

                return credentials
            else:
                logger.error(f"Account creation failed: {response.text}")

        except Exception as e:
            logger.error(f"Error creating account: {e}")

        return None

    def login(self, username, password) -> bool:
        """
        Login to Instagram account.
        """
        if not self.headers:
            self.generate_headers()

        try:
            headers = self.headers.copy()
            headers['referer'] = f'{self.BASE_URL}/accounts/login/'
            
            data = {
                'enc_password': f'#PWD_INSTAGRAM_BROWSER:0:{round(time.time())}:{password}',
                'username': username,
                'queryParams': '{}',
                'optIntoOneTap': 'false'
            }

            response = self.session.post(
                f'{self.API_BASE_URL}/web/accounts/login/ajax/',
                headers=headers,
                data=data,
                proxies=self.proxies,
                timeout=30
            )

            if response.status_code == 200:
                res_json = response.json()
                if res_json.get('authenticated') == True:
                    logger.info(f"Successfully logged in as {username}")
                    # Update cookies after login
                    self.session.cookies.update(response.cookies)
                    if 'csrftoken' in response.cookies:
                        self.headers['x-csrftoken'] = response.cookies['csrftoken']
                        cookie_parts = {c.split('=')[0]: c.split('=')[1] for c in self.headers['cookie'].split('; ')}
                        cookie_parts['csrftoken'] = response.cookies['csrftoken']
                        self.headers['cookie'] = '; '.join([f"{k}={v}" for k, v in cookie_parts.items()])
                    return True
                else:
                    logger.error(f"Login failed for {username}: {response.text}")
            else:
                logger.error(f"Login request failed with status {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"Error logging in: {e}")

        return False

    def follow_user(self, target_username_or_url: str) -> bool:
        """
        Follow a target user.
        """
        if not self.headers:
            raise ValueError("Headers not generated. Call generate_headers() first.")

        try:
            # Extract username if a URL is provided
            target_username = target_username_or_url.strip().strip('/').split('/')[-1].split('?')[0]
            
            # Step 1: Get user ID from username
            headers = self.headers.copy()
            headers['referer'] = f'{self.BASE_URL}/{target_username}/'
            
            response = self.session.get(
                f'{self.BASE_URL}/{target_username}/?__a=1&__d=dis',
                headers=headers,
                proxies=self.proxies,
                timeout=30
            )
            
            user_id = None
            if response.status_code == 200:
                try:
                    res_json = response.json()
                    # Various ways Instagram provides the ID in JSON
                    user_id = (res_json.get('graphql', {}).get('user', {}).get('id') or 
                               res_json.get('logging_page_id', '').split('_')[-1] or
                               res_json.get('items', [{}])[0].get('user', {}).get('pk'))
                except:
                    pass

            if not user_id:
                if '"id":"' in response.text:
                    user_id = response.text.split('"id":"')[1].split('"')[0]
                elif '"pk":"' in response.text:
                    user_id = response.text.split('"pk":"')[1].split('"')[0]
            
            if not user_id:
                logger.error(f"Failed to find user ID for {target_username}")
                return False

            # Step 2: Send follow request
            csrf_token = self.session.cookies.get('csrftoken') or self.headers.get('x-csrftoken')
            if csrf_token:
                headers['x-csrftoken'] = csrf_token
                cookie_parts = {c.split('=')[0]: c.split('=')[1] for c in headers['cookie'].split('; ')}
                cookie_parts['csrftoken'] = csrf_token
                headers['cookie'] = '; '.join([f"{k}={v}" for k, v in cookie_parts.items()])
            
            headers['referer'] = f'{self.BASE_URL}/{target_username}/'
            # Standard web app ID often used for actions
            headers['x-ig-app-id'] = '936619743392459' 
            
            data = {
                'container_module': 'profile',
                'nav_chain': 'UserProfilePage:profile:1',
                'user_id': user_id
            }
            
            follow_url = f'https://www.instagram.com/api/v1/friendships/create/{user_id}/'
            
            logger.info(f"Attempting to follow {target_username} (ID: {user_id})...")
            
            response = self.session.post(
                follow_url,
                headers=headers,
                data=data,
                proxies=self.proxies,
                timeout=30
            )
            
            if response.status_code == 200:
                res_json = response.json()
                if res_json.get('status') == ResponseStatus.SUCCESS.value:
                    logger.info(f"Successfully followed {target_username}")
                    return True
                else:
                    logger.error(f"Failed to follow {target_username}: {response.text}")
            else:
                logger.error(f"Follow request failed with status {response.status_code}: {response.text}")
            
        except Exception as e:
            logger.error(f"Error following user: {e}")
            
        return False
