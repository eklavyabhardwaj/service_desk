import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_test_email():
    SMTP_SERVER = "email.electrolabgroup.com"
    SMTP_PORT = 587  # Port 587 for STARTTLS
    SMTP_USERNAME = "econnect"
    SMTP_PASSWORD = "Requ!reMent$"

    # Set the recipient to an external email address for testing
    RECIPIENT_EMAILS = ["eklavyabhardwaj23@gmail.com"]
    test_issue_id = "TEST12345"
    message = f'Your File is submitted with ID : {test_issue_id}'

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = SMTP_USERNAME
    msg['To'] = ", ".join(RECIPIENT_EMAILS)
    msg['Subject'] = "Electrolab Issue Form Notification - Test"
    msg.attach(MIMEText(message, 'plain'))

    try:
        # Connect to the SMTP server and send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.set_debuglevel(1)  # Enable detailed debug output
            server.ehlo()             # Identify with the server
            server.starttls()         # Upgrade the connection to secure
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, RECIPIENT_EMAILS, msg.as_string())
            print("Test email sent successfully.")
    except Exception as e:
        print("An error occurred:", e)

if __name__ == "__main__":
    send_test_email()
