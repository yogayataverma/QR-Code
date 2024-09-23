from flask import Flask, render_template, request, redirect, url_for
import qrcode
from pymongo import MongoClient
from bson.objectid import ObjectId  # To handle MongoDB ObjectId
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Set up upload folder
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create the folder if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Load MongoDB URI and Localhost address from .env
MONGO_URI = os.getenv('MONGO_URI')
LOCALHOST_ADDRESS = os.getenv('LOCALHOST_ADDRESS')

# MongoDB configuration
client = MongoClient(MONGO_URI)
db = client['qr-code']  # Database name
schemes_collection = db.schemes  # Collection for storing schemes
participants_collection = db.participants  # Collection for storing participants

# Route to display the form for entering scheme details
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        scheme_name = request.form['scheme_name']
        scheme_description = request.form['scheme_description']
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        # Save scheme details to the MongoDB database
        scheme_id = schemes_collection.insert_one({
            "scheme_name": scheme_name,
            "scheme_description": scheme_description,
            "start_date": start_date,
            "end_date": end_date
        }).inserted_id

        # Generate QR code linking to the participation form
        qr_code_url = f'{LOCALHOST_ADDRESS}/form?scheme_id={scheme_id}'
        img = qrcode.make(qr_code_url)
        img_path = f'static/{scheme_name}.png'
        img.save(img_path)

        return render_template('display_qr.html', img_path=img_path)

    return render_template('home.html')

# Route to display the form for scheme participation
@app.route('/form', methods=['GET', 'POST'])
def form():
    scheme_id = request.args.get('scheme_id', '')

    try:
        # Convert scheme_id to ObjectId for querying MongoDB
        scheme_id = ObjectId(scheme_id)
    except Exception as e:
        return "Invalid scheme ID format!"

    # Fetch the scheme details using scheme_id
    scheme = schemes_collection.find_one({"_id": scheme_id})
    
    if not scheme:
        return "Invalid scheme ID!"

    if request.method == 'POST':
        # Get participant details from the form
        participant_name = request.form['name']
        email = request.form['email']
        mobile = request.form['mobile']
        vehicle_number = request.form['vehicle_number']
        
        # Handle file upload
        image = request.files['image_upload']
        image_filename = None
        if image and image.filename != '':
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))  # Save the file locally

        # Save the participant details to the MongoDB database
        participants_collection.insert_one({
            "scheme_id": scheme_id,  # Associate participant with the scheme
            "scheme_name": scheme["scheme_name"],
            "name": participant_name,
            "email": email,
            "mobile": mobile,
            "vehicle_number": vehicle_number,
            "image_upload": image_filename  # Save the uploaded image filename
        })

        return 'Details submitted successfully!'

    return render_template('form.html', scheme_name=scheme['scheme_name'])


if __name__ == '__main__':
    app.run(debug=True)
