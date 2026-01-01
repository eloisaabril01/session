# Instagram Account Creator

## Overview
A Python command-line tool for automating Instagram account creation using email verification.

## Project Structure
- `Acc_Gen.py` - Main application file containing the `InstagramAccountCreator` class
- `README.md` - Original project documentation

## Dependencies
- `curl_cffi` - HTTP client library with browser impersonation
- `names` - Library for generating random names

## How to Run
Run the application from the console. It will prompt for:
1. Email address
2. Verification code (sent to your email)

The tool will then create an Instagram account and optionally save credentials to a file.

## Technical Notes
- Uses `curl_cffi` for browser-like HTTP requests with Chrome impersonation
- Implements retry logic for header generation
- Generates random user agents and birth dates
- Stores credentials in `AccountCredentials` dataclass
