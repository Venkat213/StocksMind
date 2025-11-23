import os
import requests

def load_config():
    """Manually load .env file with encoding fallback"""
    env_path = ".env"
    if not os.path.exists(env_path):
        return

    content = None
    # Try UTF-8 first
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        # Fallback to UTF-16 (PowerShell default)
        try:
            with open(env_path, "r", encoding="utf-16") as f:
                content = f.read()
        except Exception:
            pass
            
    if content:
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ[key.strip()] = value.strip()

load_config()

def send_sms_otp(mobile_number, otp):
    """
    Attempts to send OTP via available SMS providers.
    Priority: Fast2SMS (India) -> Twilio (Global) -> Simulation
    """
    
    # 1. Try Fast2SMS (Best for Indian Numbers)
    fast2sms_key = os.getenv("FAST2SMS_API_KEY")
    if fast2sms_key:
        return send_via_fast2sms(fast2sms_key, mobile_number, otp)
        
    # 2. Try Twilio
    twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
    twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
    twilio_from = os.getenv("TWILIO_PHONE_NUMBER")
    
    if twilio_sid and twilio_token and twilio_from:
        return send_via_twilio(twilio_sid, twilio_token, twilio_from, mobile_number, otp)
        
    return False, "No SMS API keys found. Using Simulation Mode."

def send_via_fast2sms(api_key, mobile, otp):
    """Sends SMS using Fast2SMS API (India)"""
    url = "https://www.fast2sms.com/dev/bulkV2"
    payload = {
        "route": "otp",
        "variables_values": str(otp),
        "numbers": str(mobile)
    }
    headers = {
        "authorization": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        if data.get("return") == True:
            return True, "OTP sent via Fast2SMS"
        else:
            return False, f"Fast2SMS Error: {data.get('message')}"
    except Exception as e:
        return False, f"Fast2SMS Exception: {str(e)}"

def send_via_twilio(sid, token, from_number, to_number, otp):
    """Sends SMS using Twilio API"""
    # Ensure number has country code, default to +91 if missing and looks like Indian number
    if len(to_number) == 10 and not to_number.startswith("+"):
        to_number = "+91" + to_number
        
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = {
        "From": from_number,
        "To": to_number,
        "Body": f"Your StockMinds OTP is: {otp}"
    }
    
    try:
        response = requests.post(url, data=data, auth=(sid, token))
        if response.status_code in [200, 201]:
            return True, "OTP sent via Twilio"
        else:
            return False, f"Twilio Error: {response.text}"
    except Exception as e:
        return False, f"Twilio Exception: {str(e)}"
