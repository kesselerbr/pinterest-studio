from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from pin_manager import PinManager
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'antigravity_secret_key')

manager = PinManager()

@app.route('/')
def home():
    # Refresh config in case it changed
    manager.config = manager.load_config()
    profile = manager.get_profile()
    queue = manager.get_queue_images()
    
    auth_url = None
    if not profile:
        auth_url = manager.get_auth_url()

    return render_template('dashboard.html', 
                         config=manager.config, 
                         profile=profile, 
                         queue_count=len(queue),
                         auth_url=auth_url)

@app.route('/settings', methods=['POST'])
def settings():
    # Update config from form
    new_config = {
        'app_id': request.form.get('app_id'),
        'app_secret': request.form.get('app_secret'),
        'board_id': request.form.get('board_id'),
        'website_url': request.form.get('website_url'),
        'daily_post_limit': request.form.get('daily_post_limit')
    }
    manager.save_config(new_config)
    flash('Settings Saved!', 'success')
    return redirect(url_for('home'))

@app.route('/run', methods=['POST'])
def run_automation():
    result = manager.run_daily_post()
    if result['status'] == 'success':
        flash(f"Successfully posted {result['posted']} pins!", 'success')
    else:
        flash(f"Error: {result['message']}", 'error')
    return redirect(url_for('home'))

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if code:
        success, msg = manager.exchange_code(code)
        if success:
            flash('Successfully Connected to Pinterest!', 'success')
        else:
            flash(f'Connection Failed: {msg}', 'error')
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Content Studio on port {port}")
    app.run(host='0.0.0.0', port=port)
