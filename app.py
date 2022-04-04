# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2022 Cisco and/or its affiliates.
This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at
               https://developer.cisco.com/docs/licenses
All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
"""

__author__ = "Kim Gouweleeuw <kgouwele@cisco.com> AND Simon Fang <sifang@cisco.com>"
__copyright__ = "Copyright (c) 2022 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"

# Import Section
from flask import Flask, render_template, request
from dotenv import load_dotenv
import meraki
import os
import requests

# Load environment variables
load_dotenv()

# Global variables
app = Flask(__name__)

MERAKI_API_KEY = os.getenv('MERAKI_API_KEY')
DEVICE_NAME_FILTER = os.getenv('DEVICE_NAME_FILTER')

# Initalize SDK
dashboard = meraki.DashboardAPI(api_key = MERAKI_API_KEY)


# Template variables
organizations = []
networks = []
devices = []
selected_organization = []
selected_network = []

# Methods
def get_devices(network_id):
    global DEVICE_NAME_FILTER

    devices = dashboard.networks.getNetworkDevices(network_id)

    devices = [device for device in devices if DEVICE_NAME_FILTER in device['model']]

    return devices

def reboot_device(serial):
    response = dashboard.devices.rebootDevice(serial)

    return response

# Routes

# Main Page
@app.route('/')
def main():
    global organizations
    organizations = dashboard.organizations.getOrganizations()
    return render_template('columnpage.html', organizations = organizations, networks = [], devices = [], selected_organization = [], selected_network = [], configured_hostnames = [])

# User submits their organization and/or network selection in first rail
@app.route('/select_organization_network', methods=['POST', 'GET'])
def select_organization_network():
    global organizations
    global selected_organization
    global selected_network
    global networks
    global devices

    if request.method == 'POST':
        form_data = request.form
        print(form_data)

        organization_id = form_data['organization_id']

        for organization in organizations:
            if organization_id == organization['id']:
                selected_organization = organization 

        networks = dashboard.organizations.getOrganizationNetworks(organization_id)
        
        if 'network_id' in form_data:
            network_id = form_data['network_id']

            for network in networks:
                if network_id == network['id']:
                    selected_network = network 

            devices = get_devices(network_id)

    return render_template('columnpage.html', organizations = organizations, networks = networks, devices = devices, selected_organization = selected_organization,
         selected_network = selected_network)

@app.route('/reboot_devices', methods=['POST', 'GET'])
def reboot_devices():
    global organizations
    global selected_organization
    global selected_network
    global networks

    if request.method == 'POST':
        form_data = request.form
        app.logger.info(form_data)

        devices_to_reboot = []
        successfully_rebooted = []
        failed_to_reboot = []

        if 'serial_number' in form_data:
            form_dict = dict(form_data.lists())
            devices_to_reboot = form_dict['serial_number']
            app.logger.info(devices_to_reboot)

            for serial in devices_to_reboot:
                response = reboot_device(serial)
                app.logger.info(response)
                if response['success'] == True:
                    successfully_rebooted.append(serial)
                else:
                    failed_to_reboot.append(serial)

        app.logger.info(successfully_rebooted)
        app.logger.info(failed_to_reboot)

        if 'summary_true' in form_data:
            for device in successfully_rebooted:
                send_message(True, device)
            for device in failed_to_reboot:
                send_message(False, device)

    return render_template('columnpage.html', organizations = organizations, networks = networks, devices = devices, selected_organization = selected_organization,
         selected_network = selected_network, successfully_rebooted = successfully_rebooted, failed_to_reboot = failed_to_reboot, rebooted = True)


def send_message(response, serial):
    webex_token = os.environ['WEBEX_BOT_TOKEN']
    email = os.environ['EMAIL']

    base_url = "https://webexapis.com/v1"

    headers = {
        "Accept" : "application/json",
        "Content-Type" : "application/json",
        "Authorization" : f"Bearer {webex_token}"
    }
    
    if response == True:
        message = "We have successfully rebooted the device with serial number: '%s'" % serial
    else:
        message = "We have failed to reboot the device with serial number: '%s'" % serial

    url = f"{base_url}/messages"
    params = {
        "toPersonEmail" : email, 
        "text" : message
    }

    response = requests.post(
        url=url,
        headers=headers,
        json=params
    )
    return response

if __name__ == "__main__":
    app.run(port=5002, debug=True)