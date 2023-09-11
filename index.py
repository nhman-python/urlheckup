import asyncio
import datetime
import os
import httpx
from flask import Flask, flash, redirect, request, url_for, render_template
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired, URL
import pytz
from markupsafe import Markup

app = Flask(__name__)
app.secret_key = os.urandom(40)


def year_now():
    tz = pytz.timezone('Asia/Jerusalem')
    return datetime.datetime.now(tz=tz).year


async def redirect_history(url, ):
    redirect_urls = []
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/117.0.0.0 Safari/537.36'}
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=5) as client:
            while len(redirect_urls) <= 10:
                response = await client.get(url, headers=headers)
                redirect_urls.append({'status code': response.status_code, 'url path': response.url})

                if response.is_redirect:
                    url = response.headers['location']
                else:
                    break
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.HTTPError):
        return None
    except Exception as e:
        return None
    return redirect_urls


class UrlForm(FlaskForm):
    url = StringField('URL:', validators=[InputRequired(), URL(message="Invalid URL")])
    submit = SubmitField('סריקה')


@app.route("/", methods=["GET", "POST"])
def index():
    form = UrlForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            url = form.url.data
            redirect_result = asyncio.run(redirect_history(url))

            if redirect_result is None:
                flash('התרחשה שגיאה. אנא בדוק את כתובת האתר ונסה שוב.', 'danger')
                return redirect(url_for('index'))
            elif not redirect_result:
                flash('שגיאה: כתובת האתר אינה נגישה. אנא נסה כתובת אחרת.', 'danger')
                return redirect(url_for('index'))
            else:
                for item in redirect_result:
                    flash(Markup(
                        f'<br>:קוד מצב {item["status code"]}<br>'
                        f'נתיב:<a href="{item["url path"]}" class="btn btn-link leave-site-link" data-toggle="modal" data-target="#leaveSiteModal">{item["url path"]}</a>'),
                        'success')

                return redirect(url_for('index'))
        else:
            flash('כתובת אתר לא חוקית. אנא ספק כתובת חוקית, לדוגמא, "https://example.com".', 'danger')
            return redirect(url_for('index'))
    return render_template('index.html', form=form, year=year_now())


if __name__ == '__main__':
    app.run(debug=False)
