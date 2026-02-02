import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_register_driver():
    print(f"Testing Registration on {BASE_URL}...")
    
    url = f"{BASE_URL}/auth/register"
    
    # Multipart form data
    payload = {
        'phone': '+966500000001',
        'password': 'password123',
        'name': 'Test Driver',
        'role': 'driver',
        'email': 'driver@test.com',
        'id_name': 'Test Driver ID',
        'national_id': '1000000001',
        'birth_date': '1990-01-01'
    }
    
    # We need to send a file, even if dummy
    files = [
        ('id_photo', ('test_id.jpg', b'fakeimagebytes', 'image/jpeg'))
    ]

    try:
        response = requests.post(url, data=payload, files=files)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 201:
            print("✅ Registration Successful")
            return True
        else:
            print("❌ Registration Failed")
            return False
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

def test_login():
    print(f"\nTesting Login...")
    url = f"{BASE_URL}/auth/login"
    
    payload = {
        "phone": "+966500000001",
        "password": "password123"
    }
    
    try:
        response = requests.post(url, json=payload)
        print(f"Status Code: {response.status_code}")
        # 422? Ah, LoginRequest isn't Form? 
        # In schemas.py: class LoginRequest(BaseModel). So it expects JSON.
        # But OAuth2PasswordRequestForm expects Form.
        # My router uses: async def login(request: schemas.LoginRequest...
        # So it expects JSON. 
        
        print(f"Response: {response.text}")

        if response.status_code == 200:
            print("✅ Login Successful")
            return True
        else:
            print("❌ Login Failed")
            return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

if __name__ == "__main__":
    if test_register_driver():
        test_login()
