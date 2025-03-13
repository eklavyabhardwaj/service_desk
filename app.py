from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
import requests
import pandas as pd
import random
import re
from datetime import datetime
from flask_cors import CORS
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def is_valid_email(email):
    # A simple regex for validating an email address
    regex = r"^[^@]+@[^@]+\.[^@]+$"
    return re.match(regex, email) is not None


# Generate a random secret key for session management
random_number = random.randint(14364546454654654654651465654, 9168468484867187618761871687171)
app = Flask(__name__)
app.secret_key = str(random_number)
CORS(app)


def load_and_preprocess_data():
    base_url = 'https://erpv14.electrolabgroup.com/'
    headers = {'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'}

    # Fetch Service Person data
    endpoint_sp = 'api/resource/Service Person'
    url_sp = base_url + endpoint_sp
    params_sp = {
        'fields': '["name","employee","territory"]',
        'limit_start': 0,
        'limit_page_length': 100000000000,
    }
    response_sp = requests.get(url_sp, params=params_sp, headers=headers)
    if response_sp.status_code == 200:
        ser_per_df = pd.DataFrame(response_sp.json()['data'])
    else:
        print(f"Failed to fetch Service Person data. Status code: {response_sp.status_code}")
        return None

    # Fetch Employee data
    endpoint_emp = 'api/resource/Employee'
    url_emp = base_url + endpoint_emp
    params_emp = {
        'fields': '["name","employee_name"]',
        'limit_start': 0,
        'limit_page_length': 100000000000,
        'filters': '[["designation", "=", "Area Service Manager"],["status","=","Active"]]'
    }
    response_emp = requests.get(url_emp, params=params_emp, headers=headers)
    if response_emp.status_code == 200:
        emp_df = pd.DataFrame(response_emp.json()['data'])
    else:
        print(f"Failed to fetch Employee data. Status code: {response_emp.status_code}")
        return None

    emp_df.rename(columns={'name': 'employee'}, inplace=True)

    # Merge Employee & Service Person Data
    result_df_1 = pd.merge(emp_df, ser_per_df, on='employee', how='left')
    result_df_1.rename(columns={'territory': 'parent_territory', 'name': 'zonal_manager'}, inplace=True)

    # Add Manual Data
    sample_data = pd.DataFrame({
        "employee": ["EL1700001", "001100001"],
        "employee_name": ["Shivam Kumar", "Anuraj T. R"],
        "zonal_manager": ["Shivam Kumar", "Anuraj T. R"],
        "parent_territory": ["East", "South 3"]
    })
    result_df_1 = pd.concat([result_df_1, sample_data], ignore_index=True)
    result_df_1['zonal_manager'] = result_df_1['zonal_manager'].replace('Anuraj T. R', 'Anuraj T')
    result_df_1['zonal_manager'] = result_df_1['zonal_manager'].replace('Subrahmanyam Somagani', 'S.Somagani')
    result_df_1['zonal_manager'] = result_df_1['zonal_manager'].replace('Vivek Singh Chauhan', 'Vivek Chauhan')
    result_df_1['zonal_manager'] = result_df_1['zonal_manager'].replace('Tousif Rauf Baig Mirza', 'Tausif Mirza')

    # Fetch Customer data
    endpoint_cust = 'api/resource/Customer'
    url_cust = base_url + endpoint_cust
    params_cust = {
        'fields': '["name","territory"]',
        'limit_start': 0,
        'limit_page_length': 100000000000,
    }
    response_cust = requests.get(url_cust, params=params_cust, headers=headers)
    if response_cust.status_code == 200:
        customer_df = pd.DataFrame(response_cust.json()['data'])
    else:
        print(f"Failed to fetch Customer data. Status code: {response_cust.status_code}")
        return None

    # Fetch Territory data
    endpoint_terr = 'api/resource/Territory'
    url_terr = base_url + endpoint_terr
    params_terr = {
        'fields': '["territory_name","parent_territory"]',
        'limit_start': 0,
        'limit_page_length': 100000000000,
    }
    response_terr = requests.get(url_terr, params=params_terr, headers=headers)
    if response_terr.status_code == 200:
        territory_df = pd.DataFrame(response_terr.json()['data'])
        territory_df.rename(columns={'territory_name': 'territory'}, inplace=True)
    else:
        print(f"Failed to fetch Territory data. Status code: {response_terr.status_code}")
        return None

    result_df_2 = pd.merge(customer_df, territory_df, on='territory', how='left')
    result_df = pd.merge(result_df_1, result_df_2, on='parent_territory', how='right')

    def fill_zonal_managers(df_input):
        result = df_input.copy()
        result['zonal_manager'] = result.groupby('parent_territory')['zonal_manager'].transform(
            lambda x: x.fillna(x.dropna().iloc[0] if not x.dropna().empty else x)
        )
        mask = result['zonal_manager'].isna()
        if mask.any():
            territory_zm_dict = {}
            for terr in result.loc[mask, 'parent_territory'].unique():
                zm_values = result[(result['territory'] == terr) & (result['zonal_manager'].notna())]['zonal_manager']
                if not zm_values.empty:
                    territory_zm_dict[terr] = zm_values.iloc[0]
            result.loc[mask, 'zonal_manager'] = result.loc[mask, 'parent_territory'].map(territory_zm_dict)
        return result

    result_df = fill_zonal_managers(result_df)
    result_df = result_df[["name", "zonal_manager"]]
    result_df.rename(columns={'name': 'customer'}, inplace=True)
    return result_df.set_index('customer')['zonal_manager'].to_dict()


customer_zonal_manager_map = load_and_preprocess_data()


# -----------------------------
# Existing routes
# -----------------------------
@app.route('/get_zonal_manager', methods=['GET'])
def get_zonal_manager():
    customer_name = request.args.get('customer')
    if customer_name and customer_zonal_manager_map:
        zonal_manager = customer_zonal_manager_map.get(customer_name)
        if zonal_manager:
            return jsonify({'zonal_manager': zonal_manager})
        else:
            return jsonify({'zonal_manager': 'Not Found'})
    else:
        return jsonify({'error': 'Customer not provided or data not loaded'}), 400


@app.route('/get_issue_table', methods=['GET'])
def get_issue_table():
    base_url = 'https://erpv14.electrolabgroup.com/'
    endpoint = 'api/resource/Serial No'
    url = base_url + endpoint
    search_term = request.args.get('search', '')
    filters = f'[["name", "like", "%{search_term}%"]]'
    params = {
        'fields': '["name", "item_name", "item_code", "customer_instrument_id", "customer", "custom_amc_type_name"]',
        'limit_start': 0,
        'limit_page_length': 20,
        'filters': filters
    }
    headers = {'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'}
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        df = pd.DataFrame(data['data'])
        if df.empty:
            return jsonify([])
        if 'name' in df.columns:
            df.rename(columns={'name': 'serial_no'}, inplace=True)
        if 'custom_amc_type_name' in df.columns:
            df.rename(columns={'custom_amc_type_name': 'amc_type'}, inplace=True)
        expected_columns = ['serial_no', 'item_name', 'item_code', 'customer_instrument_id', 'customer', 'amc_type']
        missing = [col for col in expected_columns if col not in df.columns]
        if missing:
            return jsonify([])
        result_data = df[expected_columns].dropna().to_dict(orient='records')
        return jsonify(result_data)
    else:
        return jsonify({"error": "Failed to fetch data from API"}), 500


@app.route('/get_serial_details', methods=['GET'])
def get_serial_details():
    serial_no = request.args.get('serial_no', '')
    if not serial_no:
        return jsonify({'error': 'Serial number is required'}), 400

    def fetch_data():
        base_url = 'https://erpv14.electrolabgroup.com/'
        headers = {'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'}

        serial_response = requests.get(
            f'{base_url}api/resource/Serial No',
            params={
                'fields': '["name", "warranty_expiry_date", "customer", "item_name", "custom_amc_type_name"]',
                'filters': f'[["name", "=", "{serial_no}"]]',
                'limit_start': 0,
                'limit_page_length': 1,
            },
            headers=headers
        )

        if serial_response.status_code != 200:
            return None

        data = serial_response.json().get('data', [])
        if not data:
            print("⚠️ No serial number found in ERP!")
            return None

        ser_per_df = pd.DataFrame(data)

        address_response = requests.get(
            f'{base_url}api/resource/Address',
            params={
                'fields': '["name", "links.link_name"]',
                'limit_start': 0,
                'limit_page_length': 100000000000,
            },
            headers=headers
        )

        if address_response.status_code != 200:
            return None

        address_df = pd.DataFrame(address_response.json()['data'])
        address_df.rename(columns={'name': 'customer_address', 'link_name': 'customer'}, inplace=True)
        address_df = address_df.drop_duplicates(subset='customer', keep='first')

        return pd.merge(address_df, ser_per_df, on='customer', how='inner')

    df = fetch_data()

    if df is None or df.empty:
        print("Serial number not found in fetched data.")
        return jsonify({'error': 'Serial number not found'}), 404

    row = df[df['name'] == serial_no]
    if row.empty:
        return jsonify({'error': 'Serial number not found'}), 404

    customer_val = row['customer'].iloc[0]
    zonal_manager = customer_zonal_manager_map.get(customer_val, '')
    warranty_expiry_date = row['warranty_expiry_date'].iloc[0]

    try:
        warranty_date = datetime.strptime(warranty_expiry_date, '%Y-%m-%d').date()
        today = datetime.today().date()
        maintenance_status = "Under Warranty" if warranty_date >= today else "Out of Warranty"
    except Exception as e:
        maintenance_status = "Unknown"

    result = {
        'customer': customer_val,
        'customer_address': row['customer_address'].iloc[0] if 'customer_address' in row.columns else '',
        'warranty_expiry_date': warranty_expiry_date,
        'item_name': row['item_name'].iloc[0] if 'item_name' in row.columns else '',
        'maintenance_status': maintenance_status,
        'zonal_manager': zonal_manager,
        'amc_type': row['custom_amc_type_name'].iloc[0] if 'custom_amc_type_name' in row.columns else ''
    }

    return jsonify(result)


# Global SMTP_SSL configuration using your provided settings
SMTP_SERVER = "email.electrolabgroup.com"
SMTP_PORT = 465
SMTP_USERNAME = "econnect"
SMTP_PASSWORD = "Requ!reMent$"
SMTP_EMAIL = "econnect@electrolabgroup.com"  # Sender email


@app.route('/submit', methods=['POST'])
def submit_form():
    base_url = 'https://erpv14.electrolabgroup.com/'
    endpoint = 'api/resource/Issue'
    url = base_url + endpoint
    headers = {
        'Authorization': 'token 3ee8d03949516d0:6baa361266cf807',
        'Content-Type': 'application/json',
        'Expect': ''  # Disable the default Expect header
    }
    try:
        # Check email validity before processing form data
        email = request.form.get('custom_contact_email', '').strip()
        if not email or not is_valid_email(email):
            flash("Invalid email address. Please enter a valid email.", "error")
            return redirect(url_for('issue'))

        form_data = {
            "naming_series": request.form.get('naming_series'),
            "status": request.form.get('status'),
            "subject": request.form.get('description', '')[:20],
            "priority": request.form.get('priority'),
            "issue_type": ", ".join(request.form.getlist('issue_type')) if request.form.getlist('issue_type') else "NA",
            "serial_no": request.form.get('serial_no'),
            "customer": request.form.get('customer'),
            "custom_contact_email": email,
            "issue_generate_date": request.form.get('issue_generate_date'),
            "zonal_manager": request.form.get('zonal_manager'),
            "territory": request.form.get('territory'),
            "job_type": request.form.get('job_type') or "ONLINE SUPPORT",
            "issue_responsibility_with": request.form.get('issue_responsibility_with'),
            "prio_po_number": request.form.get('prio_po_number') or "NA",
            "amc_type": request.form.get('amc_type') or "Out Of Warranty",
            "description": (
                f"{request.form.get('description', '').strip()}"
                f"<br><br><b>{request.form.get('contact_person_name', '').strip()} "
                f"{request.form.get('phone_extension', '').strip()}"
                f"{request.form.get('phone_number', '').strip()}</b>"
            )
        }

        if not form_data['issue_generate_date']:
            form_data['issue_generate_date'] = datetime.today().strftime('%Y-%m-%d')
        received_dates = request.form.getlist('issue_received_date[]')
        form_data['issue_received_date'] = received_dates[0] if received_dates else form_data['issue_generate_date']
        issue_data = []
        item_serial_name = request.form.getlist('serial_no[]')
        item_names = request.form.getlist('item_name[]')
        item_codes = request.form.getlist('item_code[]')
        customer_ids = request.form.getlist('customer_instrument_id[]')
        for i in range(len(item_names)):
            if item_names[i].strip():
                issue_data.append({
                    "serial_no": item_serial_name[i],
                    "item_name": item_names[i],
                    "item_code": item_codes[i],
                    "customer_instrument_id": customer_ids[i]
                })
        if issue_data:
            form_data["issue_details"] = issue_data

        print("Issue Form Data:", form_data)
        response = requests.post(url, json=form_data, headers=headers)
        print("ERP Response:", response.text)

        if response.ok:
            try:
                issue_response = response.json()
                issue_name = issue_response.get("data", {}).get("name", "Unknown")

                RECIPIENT_EMAILS = [email]
                message = f'Your File is submitted with ID : {issue_name}'

                msg = MIMEMultipart()
                msg['From'] = SMTP_EMAIL
                msg['To'] = ", ".join(RECIPIENT_EMAILS)
                msg['Subject'] = "Electrolab Issue Form Notification"
                msg.attach(MIMEText(message, 'plain'))

                try:
                    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                        server.login(SMTP_USERNAME, SMTP_PASSWORD)
                        server.sendmail(SMTP_EMAIL, RECIPIENT_EMAILS, msg.as_string())
                        print("Email sent successfully.")
                except Exception as e:
                    print("An error occurred while sending email:", e)
            except Exception as e:
                issue_name = "Unknown"
            flash(
                f'Request submitted successfully! Issue Name: {issue_name}, for any query contact us on: service@electrolabgroup.com or +91 9167839674',
                'success')
        else:
            flash(f'Error {response.status_code}, please check the form and submit again.', 'error')
    except Exception as e:
        print("Exception details:", str(e))
        flash(f'Error occurred: {str(e)}', 'error')
    return redirect(url_for('issue'))


@app.route('/submit2', methods=['POST'])
def submit_form_warranty():
    base_url = 'https://erpv14.electrolabgroup.com/'
    endpoint = 'api/resource/Warranty Claim'
    url = base_url + endpoint
    headers = {
        'Authorization': 'token 3ee8d03949516d0:6baa361266cf807',
        'Content-Type': 'application/json'
    }
    try:
        # Check email validity before processing warranty form data
        email = request.form.get('custom_contact_email', '').strip()
        if not email or not is_valid_email(email):
            flash("Invalid email address. Please enter a valid email.", "error")
            return redirect(url_for('warranty'))

        form_data = {
            "naming_series": request.form.get('naming_series'),
            "status": request.form.get('status'),
            "custom_contact_email": email,
            "priority": request.form.get('priority'),
            "customer": request.form.get('customer'),
            "serial_no": request.form.get('serial_no'),
            "issue_type": request.form.get('issue_type'),
            "complaint_date": request.form.get('complaint_date'),
            "zonal_manager": request.form.get('zonal_manager'),
            "territory": request.form.get('territory'),
            "job_type": request.form.get('job_type'),
            "warranty_claim_responsibility_with": request.form.get('warranty_claim_responsibility_with'),
            "prio_po_number": request.form.get('prio_po_number'),
            "amc_type": request.form.get('amc_type'),
            "warranty_amc_status": request.form.get('warranty_amc_status'),
            "complaint": request.form.get('complaint'),
            "warranty_expiry_date": request.form.get('warranty_expiry_date'),
            "customer_name": request.form.get('customer_name'),
            "customer_address": request.form.get('customer_address'),
            "complaint_raised_by": (
                    request.form.get('contact_person_name', '') + " " + request.form.get('phone_number', '')
            )
        }
        if not form_data['complaint_date']:
            form_data['complaint_date'] = datetime.today().strftime('%Y-%m-%d')
        received_dates = request.form.getlist('claim_received_date[]')
        form_data['claim_received_date'] = received_dates[0] if received_dates else form_data['complaint_date']

        print("Warranty Form Data:", form_data)
        response = requests.post(url, json=form_data, headers=headers)
        if response.ok:
            try:
                warranty_response = response.json()
                warranty_name = warranty_response.get("data", {}).get("name", "Unknown")

                RECIPIENT_EMAILS = [email]
                message = f'Your File is submitted with ID : {warranty_name}'

                msg = MIMEMultipart()
                msg['From'] = SMTP_EMAIL
                msg['To'] = ", ".join(RECIPIENT_EMAILS)
                msg['Subject'] = "Electrolab Warranty Form Notification"
                msg.attach(MIMEText(message, 'plain'))

                try:
                    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
                        server.login(SMTP_USERNAME, SMTP_PASSWORD)
                        server.sendmail(SMTP_EMAIL, RECIPIENT_EMAILS, msg.as_string())
                        print("Email sent successfully.")
                except Exception as e:
                    print("An error occurred:", e)
            except Exception as e:
                warranty_name = "Unknown"
            flash(
                f'Request submitted successfully! Warranty Name: {warranty_name}, for any query contact us on: service@electrolabgroup.com or +91 9167839674',
                'success')
        else:
            flash(f'Error {response.status_code}, please check the form and submit again.', 'error')
    except Exception as e:
        print("Exception details:", str(e))
        flash(f'Error occurred: {str(e)}', 'error')
    return redirect(url_for('warranty'))


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/issue')
def issue():
    return render_template('issue.html')


@app.route('/warranty')
def warranty():
    return render_template('warranty.html')


@app.route('/terms')
def tnc():
    return render_template('tnc.html')


@app.route('/search_serials', methods=['GET'])
def search_serials():
    search_term = request.args.get('query', '')
    if not search_term:
        return jsonify([])

    base_url = 'https://erpv14.electrolabgroup.com/'
    endpoint = 'api/resource/Serial No'
    url = f"{base_url}{endpoint}"
    headers = {'Authorization': 'token 3ee8d03949516d0:6baa361266cf807'}

    filters = f'[["customer","is","set"],["name", "like", "%{search_term}%"]]'
    params = {
        'fields': '["name"]',
        'limit_start': 0,
        'limit_page_length': 10,
        'filters': filters
    }
    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json().get('data', [])
        serials = [item['name'] for item in data]
        return jsonify(serials)
    else:
        print(f"Error fetching data from ERP. Status: {response.status_code}, Response: {response.text}")
        return jsonify([])


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
