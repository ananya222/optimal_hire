from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

# Import your Blueprints from the other files
from candidate_routes import candidate_bp
from company_routes import company_bp
from resume_routes import resume_bp

load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration for file uploads (used by resume_routes)
app.config['UPLOAD_FOLDER'] = 'uploads/resumes'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit

# Create upload folder if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Register Blueprints with a clear URL prefix
# Now all candidate routes start with /api/profiles/candidate
app.register_blueprint(candidate_bp, url_prefix='/api/profiles')
app.register_blueprint(company_bp, url_prefix='/api/profiles')
app.register_blueprint(resume_bp, url_prefix='/api/profiles')

@app.route('/')
def health_check():
    return {"status": "Profile Service is running"}, 200

if __name__ == '__main__':
    app.run(debug=True, port=5001)