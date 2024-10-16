from flask import Flask, request, render_template_string
import os
import PyPDF2
import re
import requests
import pandas as pd
from bs4 import BeautifulSoup

app = Flask(__name__)

# Create necessary directories
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# Load job listings from CSV
def load_job_listings():
    """Load job listings from a CSV file."""
    df = pd.read_csv('job_listings.csv')  # Adjust the path to your CSV file
    return df

# Internship scraping function with error handling
def fetch_internships(query):
    """Fetch internships based on skills from Internshala with error handling."""
    url = f"https://internshala.com/internships/keywords-{query.replace(' ', '-')}"
    
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        internships = []
        listings = soup.find_all('div', class_='internship_meta')

        for listing in listings[:10]:  # Limit to top 10 internships
            try:
                title = listing.find('h3').get_text(strip=True)
                company_tag = listing.find('a', class_='link_display_like_text')
                company = company_tag.get_text(strip=True) if company_tag else "N/A"
                link = "https://internshala.com" + listing.find('a')['href']
                internships.append({'title': title, 'company': company, 'link': link})
            except AttributeError as e:
                print(f"Error parsing internship listing: {e}")
                continue  # Skip any listings with missing data

        return internships

    except Exception as e:
        print(f"Error fetching internships: {e}")
        return []

def parse_resume(file):
    """Extract skills from the uploaded resume."""
    skills = set()
    with open(file, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            skills.update(re.findall(r'\b(?:Python|Java|HTML|CSS|JavaScript|Machine Learning)\b', text, re.IGNORECASE))
    return skills

def get_job_suggestions(skills):
    """Get job suggestions based on skills."""
    job_listings = load_job_listings()
    suggestions = []
    
    for _, row in job_listings.iterrows():
        required_skills = row['Required_Skills'].split(', ')
        if any(skill.strip() in required_skills for skill in skills):
            suggestions.append(row['Job_Title'])

    return suggestions[:10]  # Limit to top 10 job suggestions

# Enhanced HTML template with Bootstrap
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Internship Finder</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css">
    <style>
        body {
            background-color: #f8f9fa;
            padding-top: 50px;
        }
        .container {
            max-width: 900px;
            margin: auto;
            background: #ffffff;
            padding: 30px;
            box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
            border-radius: 10px;
        }
        h1 {
            color: #343a40;
            font-weight: bold;
            text-align: center;
        }
        .internship-list, .job-suggestions {
            padding: 0;
            list-style-type: none;
        }
        .internship-item, .job-item {
            background: #17a2b8;
            color: white;
            margin: 5px 0;
            padding: 15px;
            border-radius: 5px;
            transition: transform 0.2s;
        }
        .internship-item:hover, .job-item:hover {
            transform: scale(1.02);
        }
        a {
            color: white;
            text-decoration: none;
        }
        .row {
            margin-top: 20px;
        }
        .column {
            flex: 50%;
            padding: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Find Internships Based on Your Resume</h1>
        <form action="/" method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label for="resume">Upload Your Resume (PDF)</label>
                <input type="file" class="form-control" name="resume" required>
            </div>
            <button type="submit" class="btn btn-primary btn-block">Find Internships</button>
        </form>
        
        {% if internships or job_suggestions %}
        <div class="row mt-4">
            <div class="column">
                <h2 class="text-center">Top Internship Opportunities</h2>
                <ul class="internship-list">
                    {% for internship in internships %}
                    <li class="internship-item">
                        <strong>{{ internship.title }}</strong> at {{ internship.company }}<br>
                        <a href="{{ internship.link }}" target="_blank">View Details</a>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            <div class="column">
                <h2 class="text-center">Job Suggestions</h2>
                <ul class="job-suggestions">
                    {% for job in job_suggestions %}
                    <li class="job-item">
                        <strong>{{ job }}</strong> <!-- Correctly display job titles -->
                    </li>
                    {% endfor %}
                </ul>
            </div>
        </div>
        <a href="/" class="btn btn-secondary btn-block mt-3">Try Again</a>
        {% endif %}
    </div>
    <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.5.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>'''

@app.route('/', methods=['GET', 'POST'])
def index():
    internships = None
    job_suggestions = []  # Initialize job suggestions

    if request.method == 'POST':
        resume_file = request.files['resume']
        resume_path = os.path.join('uploads', resume_file.filename)
        resume_file.save(resume_path)

        resume_skills = parse_resume(resume_path)
        skill_query = ' '.join(resume_skills)

        internships = fetch_internships(skill_query)

        # Fetch job suggestions from the CSV file
        job_suggestions = get_job_suggestions(resume_skills)

        os.remove(resume_path)

    return render_template_string(HTML_TEMPLATE, internships=internships, job_suggestions=job_suggestions)

if __name__ == '__main__':
    app.run(debug=True)
