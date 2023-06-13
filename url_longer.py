import aiohttp
import asyncio
from flask import Flask, abort, render_template_string, session, request, jsonify
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField
from wtforms.validators import InputRequired
import re
from urllib.parse import unquote
import os
all_urls = ['/', '/json']
app = Flask(__name__)
app.secret_key = os.urandom(40)
csrf = CSRFProtect(app)


@app.before_request
def before_request():
    if request.path in all_urls:
        return
    abort(404)


class URLForm(FlaskForm):
    url = StringField('Enter a URL:', validators=[InputRequired()])


async def get_redirect_info(session_data, short_url):
    try:
        if not short_url.startswith('https://'):
            raise ValueError('רק כתובות HTTPS מותרות.')

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        async with session_data.get(short_url, allow_redirects=True, timeout=10, headers=headers) as response:
            redirect_info = []

            for redirect_history in response.history:
                redirect_info.append({
                    'status_code': redirect_history.status,
                    'url': str(redirect_history.url)
                })

            redirect_info.append({
                'status_code': response.status,
                'url': str(response.url)
            })

            return redirect_info
    except aiohttp.ClientError as e:
        error_info = {
            'error': str(e)
        }
        return [error_info]
    except aiohttp.ClientConnectorError:
        error_info = {
            'error': 'יצירת חיבור נכשלה או ש-HTTPS אינו נתמך על ידי השרת.'
        }
        return [error_info]
    except asyncio.TimeoutError:
        error_info = {
            'error': 'החיבור לא הצליח.'
        }
        return [error_info]
    except ValueError as e:
        error_info = {
            'error': str(e)
        }
        return [error_info]
    except Exception as e:
        error_info = {'error': str(e)}
        return [error_info]


async def process_url(url):
    async with aiohttp.ClientSession() as SESSION:
        try:
            redirect_info = await get_redirect_info(SESSION, url)
            return redirect_info
        except aiohttp.ClientError as e:
            error_info = {
                'error': str(e)
            }
            return [error_info]
        except asyncio.TimeoutError:
            error_info = {
                'error': 'Connection timed out.'
            }
            return [error_info]


def is_potential_xss(user_input):
    # Define patterns for potential XSS
    # Decode the user input
    decoded_input = unquote(user_input)
    xss_patterns = [
        r"<script[^>]*>[^<]*<\/script>",
        r"<[^>]+on\w+=(\'|\")[^>]+>",
        # Add more patterns as needed
    ]

    # Check if any of the patterns match the user input
    for pattern in xss_patterns:
        if re.search(pattern, user_input, re.IGNORECASE):
            return True
        else:
            # Check if any of the patterns match the user input
            for pattern in xss_patterns:
                if re.search(pattern, decoded_input, re.IGNORECASE):
                    return True

    return False


@app.route("/", methods=["GET", "POST"])
def home():
    form = URLForm()

    if form.validate_on_submit():
        url = form.url.data

        # Perform XSS check on user-supplied input
        user_input = url
        if is_potential_xss(user_input):
            # Handle potential XSS
            return render_template_string(main_page, error_message="Potential XSS detected", form=form)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        redirect_info = loop.run_until_complete(process_url(url))
        loop.close()

        if redirect_info and 'error' not in redirect_info[0]:
            session['last_url'] = url
            return render_template_string(main_page, redirect_info=redirect_info, form=form)
        else:
            error_message = redirect_info[0]['error'] if redirect_info else 'Error: Unknown error'
            return render_template_string(main_page, error_message=error_message, form=form)

    else:
        last_url = session.get('last_url', '')
        return render_template_string(main_page, last_url=last_url, form=form)


main_page = """
<!DOCTYPE html>
<html>
<head>
    <title>מאריך קישורים מקוצרים</title>
    <style>
        body {
            font-family: 'Courier New', monospace;
            margin: 0;
            background-repeat: repeat;
            background-position: center;
            background-color: #000;
            color: #0f0;
            text-shadow: 1px 1px 2px #0f0;
        }
        h1 {
            text-align: center;
            font-size: 36px;
            margin-top: 50px;
        }
        form {
            text-align: center;
            margin-top: 30px;
        }
        label {
            font-weight: bold;
            font-size: 20px;
        }
        input[type="text"] {
            width: 300px;
            padding: 5px;
            font-family: 'Courier New', monospace;
            font-size: 16px;
            background-color: #000;
            color: #0f0;
            border: 1px solid #0f0;
        }
        button[type="submit"] {
            padding: 5px 10px;
            background-color: #0f0;
            color: #000;
            border: none;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-size: 16px;
        }
        .redirect-info {
            margin-top: 30px;
            text-align: center;
            display: none;
        }
        .redirect-info-item {
            font-size: 18px;
            margin-bottom: 10px;
        }
        .last-url {
            margin-top: 30px;
            text-align: center;
            display: none;
        }
        .error-message {
            color: #f00;
            text-align: center;
            margin-top: 30px;
        }
    </style>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            var redirectInfo = document.querySelector('.redirect-info');
            var lastUrl = document.querySelector('.last-url');
            var errorMessage = document.querySelector('.error-message');

            function showLines(element, lines) {
                element.innerHTML = '';
                var index = 0;
                element.style.display = 'block';

                function typeLine() {
                    if (index < lines.length) {
                        element.innerHTML += lines[index] + '<br>';
                        index++;
                        setTimeout(typeLine, 140);
                    }
                }

                typeLine();
            }

            {% if redirect_info %}
                showLines(redirectInfo, [
                    "<h2>מידע על הפניה:</h2>",
                    "<ul>",
                    {% for info in redirect_info %}
                        "<li><strong>סטטוס קוד:</strong> {{ info['status_code'] }}</li>",
                        "<li><strong>קישור:</strong> {{ info['url'] }}</li>",
                    {% endfor %}
                    "</ul>"
                ]);
            {% elif last_url %}
                showLines(lastUrl, [
                    "<h2>קישור אחרון:</h2>",
                    "<p>{{ last_url }}</p>"
                ]);
            {% elif error_message %}
                errorMessage.style.display = 'block';
                errorMessage.innerHTML = '{{ error_message }}';
            {% else %}
                errorMessage.style.display = 'block';
                errorMessage.innerHTML = 'שגיאה: אנא הזן כתובת';
            {% endif %}
        });
    </script>
</head>
<body>
    <h1>מאריך קישורים מקוצרים</h1>
    <form method="POST" action="/">
        {{ form.csrf_token }}
        <label for="url">הזן כתובת:</label>
        {{ form.url }}
        <button type="submit">בדיקה</button>
    </form>
    <div class="redirect-info"></div>
    <div class="last-url"></div>
    <div class="error-message"></div>
</body>
</html>
"""


@app.after_request
def add_csp_and_cookie_headers(response):
    csp_headers = {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline' 'unsafe-eval'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data:",
        'font-src': "'self'",
        'frame-ancestors': "'self'",
        'object-src': "'self'",
        'media-src': "'self'",
        'connect-src': "'self'",
    }

    csp_header_value = "; ".join(f"{key} {value}" for key, value in csp_headers.items())
    response.headers.set("Content-Security-Policy", csp_header_value)

    response.headers.set("X-Frame-Options", "SAMEORIGIN")
    response.headers.set("Server", "")  # Remove or obfuscate the server information
    response.headers.set("Set-Cookie", "SameSite=Lax; HttpOnly")  # Include SameSite and HttpOnly flags
    response.headers.set("X-Content-Type-Options", "nosniff")

    return response


async def process_url_json(url):
    async with aiohttp.ClientSession() as SESSION:
        try:
            redirect_info = await get_redirect_info(SESSION, url)
            return {
                "start_url": url,
                "final_url": redirect_info[-1]["url"],
                "final_domain": redirect_info[-1]["url"].split("//")[1].split("/")[0],
                "route_log": [info["url"] for info in redirect_info]
            }
        except aiohttp.ClientError as e:
            return {"error": str(e)}
        except asyncio.TimeoutError:
            return {"error": "Connection timed out."}


@csrf.exempt
@app.route('/json', methods=["GET", "POST"])
def data_json():
    url = request.form.get("url")
    if url not in [None, '', ' ']:
        # Perform XSS check on user-supplied input
        user_input = url

        if is_potential_xss(user_input):
            # Handle potential XSS
            return jsonify({"error": "Potential XSS detected"})

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        redirect_info = loop.run_until_complete(process_url_json(url))
        loop.close()

        if redirect_info and 'error' not in redirect_info:
            return jsonify(redirect_info)
        else:
            error_message = redirect_info.get('error', 'Unknown error')
            return jsonify({"error": error_message})
    else:
        return jsonify({"error": "URL not provided"})


if __name__ == "__main__":
    app.run()
