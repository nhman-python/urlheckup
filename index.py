import asyncio
import os
import httpx
from flask import Flask, render_template, flash, redirect, request, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import InputRequired, URL
import logging

logging.basicConfig(filemode='a', filename='log-redict.log')
app = Flask(__name__)
app.secret_key = os.urandom(40)


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
        logging.error(f'error: {e}')
        return None
    return redirect_urls


class UrlForm(FlaskForm):
    url = StringField('URL', validators=[InputRequired(), URL(message="Invalid URL")])
    submit = SubmitField('Submit')


@app.route("/", methods=["GET", "POST"])
def index():
    form = UrlForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            url = form.url.data
            redirect_result = asyncio.run(redirect_history(url))

            if redirect_result is None:
                flash('An error occurred. Please check the URL and try again.', 'danger')
                return redirect(url_for('index'))
            elif not redirect_result:
                flash('Error: The URL is not accessible. Please try a different one.', 'danger')
                return redirect(url_for('index'))
            else:
                flash('Success: Here is the redirect history', 'success')
                return render_template('index.html', form=form, redirect=redirect_result)
        else:
            flash('Invalid URL. Please provide a valid one, for example, "https://example.com".', 'danger')
            return redirect(url_for('index'))
    return render_template('index.html', form=form)


if __name__ == '__main__':
    app.run(debug=False)