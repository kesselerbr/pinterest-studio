import requests
import json
import os
import shutil
import datetime
import base64
import time

CONFIG_PATH = 'config.json'

class PinManager:
    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        defaults = {
            "app_id": "1543663",
            "app_secret": "3243f6a490942584cd1d8015f490d4509a359936",
            "board_id": "336784947074357903",
            "redirect_uri": "https://marcela-studio.onrender.com/callback",
            "website_url": "https://rad-mochi-11c837.netlify.app",
            "daily_post_limit": "5"
        }
        
        if not os.path.exists(CONFIG_PATH):
            return defaults
            
        try:
            with open(CONFIG_PATH, 'r') as f:
                saved_config = json.load(f)
                # Merge saved config onto defaults (saved takes precedence for tokens, etc.)
                defaults.update(saved_config)
                return defaults
        except:
            return defaults

    def save_config(self, new_config):
        self.config.update(new_config)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(self.config, f, indent=4)

    def get_auth_url(self):
        app_id = self.config.get('app_id')
        redirect_uri = self.config.get('redirect_uri')
        if not app_id or not redirect_uri:
            return None
        scopes = "boards:read,boards:write,pins:read,pins:write,user_accounts:read"
        return f"https://www.pinterest.com/oauth/?client_id={app_id}&redirect_uri={redirect_uri}&response_type=code&scope={scopes}"

    def exchange_code(self, code):
        app_id = self.config.get('app_id')
        app_secret = self.config.get('app_secret')
        redirect_uri = self.config.get('redirect_uri')
        
        token_url = "https://api.pinterest.com/v5/oauth/token"
        auth_str = requests.auth.HTTPBasicAuth(app_id, app_secret)
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri
        }
        
        try:
            response = requests.post(token_url, auth=auth_str, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            updates = {
                'access_token': token_data['access_token'],
                'refresh_token': token_data['refresh_token']
            }
            self.save_config(updates)
            return True, "Authenticated successfully"
        except Exception as e:
            return False, str(e)

    def get_profile(self):
        access_token = self.config.get('access_token')
        if not access_token:
            return None
            
        url = "https://api.pinterest.com/v5/user_account"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def get_queue_images(self):
        input_folder = self.config.get('input_folder', 'inputs')
        if not os.path.exists(input_folder):
            os.makedirs(input_folder)
            
        valid = ('.jpg', '.jpeg', '.png')
        return [f for f in os.listdir(input_folder) if f.lower().endswith(valid)]

    def run_daily_post(self):
        images = self.get_queue_images()
        limit = int(self.config.get('daily_post_limit', 5))
        to_post = images[:limit]
        
        if not to_post:
            return {"status": "warning", "message": "No images in input folder"}

        access_token = self.config.get('access_token')
        board_id = self.config.get('board_id')
        website_url = self.config.get('website_url')

        if not access_token or not board_id:
            return {"status": "error", "message": "Missing Configuration (Token or Board ID)"}

        results = []
        for img in to_post:
            success = self._post_single_pin(img, access_token, board_id, website_url)
            results.append(success)
            if success:
                self._move_to_posted(img)
                time.sleep(2) # Small delay
        
        return {"status": "success", "posted": len([r for r in results if r]), "total": len(to_post)}

    def _post_single_pin(self, img_name, token, board_id, link):
        input_folder = self.config.get('input_folder', 'inputs')
        img_path = os.path.join(input_folder, img_name)
        
        # Default Metadata
        clean_name = os.path.splitext(img_name)[0].replace("-", " ").replace("_", " ")
        title = f"{self.config.get('default_title_prefix', '')}{clean_name.title()}"
        description = f"{title}. Get your daily numerology reading at {link}. #numerology #affirmations"
        
        # Check for JSON Sidecar (SEO)
        json_name = os.path.splitext(img_name)[0] + '.json'
        json_path = os.path.join(input_folder, json_name)
        
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                    if meta.get('title'): title = meta.get('title')
                    if meta.get('description'): description = meta.get('description')
                    if meta.get('link'): link = meta.get('link') # Override link if specific
            except Exception as e:
                print(f"Error reading JSON for {img_name}: {e}")

        url = "https://api.pinterest.com/v5/pins"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            with open(img_path, "rb") as img_file:
                b64_string = base64.b64encode(img_file.read()).decode('utf-8')

            content_type = "image/png" if img_name.lower().endswith('.png') else "image/jpeg"

            payload = {
                "board_id": board_id,
                "media_source": {
                    "source_type": "image_base64",
                    "content_type": content_type,
                    "data": b64_string
                },
                "link": link,
                "title": title,
                "description": description
            }
            
            response = requests.post(url, headers=headers, json=payload)
            return response.status_code == 201
        except Exception as e:
            print(f"Error posting {img_name}: {e}")
            return False

    def _move_to_posted(self, img_name):
        input_folder = self.config.get('input_folder', 'inputs')
        posted_folder = self.config.get('posted_folder', 'posted')
        
        date_str = datetime.datetime.now().strftime("%Y-%m-%d")
        dest_dir = os.path.join(posted_folder, date_str)
        
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            
        shutil.move(os.path.join(input_folder, img_name), os.path.join(dest_dir, img_name))
