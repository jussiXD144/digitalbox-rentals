import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader

# Setup Jinja environment for email templates
template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'emails')
if not os.path.exists(template_dir):
    os.makedirs(template_dir, exist_ok=True)
    
env = Environment(loader=FileSystemLoader(template_dir))

def get_smtp_config():
    return {
        'server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'port': int(os.getenv('SMTP_PORT', 587)),
        'username': os.getenv('SMTP_USERNAME', ''),
        'password': os.getenv('SMTP_PASSWORD', ''),
        'from_email': os.getenv('SMTP_FROM_EMAIL', os.getenv('SMTP_USERNAME', ''))
    }

def send_email(to_email: str, subject: str, html_content: str):
    config = get_smtp_config()
    
    # If no password is provided, we skip sending (e.g. for local dev without env vars)
    if not config['password']:
        print(f"Skipping email to {to_email} (No SMTP_PASSWORD configured)")
        return
        
    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = f"DigitalBox <{config['from_email']}>"
    msg['To'] = to_email

    part = MIMEText(html_content, 'html')
    msg.attach(part)

    try:
        server = smtplib.SMTP(config['server'], config['port'])
        server.ehlo()
        server.starttls()
        server.login(config['username'], config['password'])
        server.sendmail(config['from_email'], to_email, msg.as_string())
        server.quit()
        print(f"Successfully sent email to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}. Error: {e}")

def send_welcome_email(to_email: str):
    template = env.get_template('welcome.html')
    html_content = template.render(email=to_email)
    send_email(to_email, "Willkommen bei DigitalBox! 🚀", html_content)

def send_subscription_email(to_email: str, plan_name: str, has_crypto: bool = False):
    template = env.get_template('subscription.html')
    html_content = template.render(email=to_email, plan_name=plan_name, has_crypto=has_crypto)
    send_email(to_email, f"Deine {plan_name.capitalize()}-Box ist bereit! 📦", html_content)
