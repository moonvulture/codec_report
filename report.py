import requests
import xml.etree.ElementTree as ET
import re
import csv
import os
import yaml

from requests.auth import HTTPBasicAuth
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


system_info = {}
CONFIG_FILE = 'config.yaml'
CONFIG = None
BASIC_AUTH = None
HEADERS = {'Content-Type': 'text/xml'}

def load_config():
    global CONFIG, BASIC_AUTH
    with open(CONFIG_FILE) as f:
        CONFIG = yaml.safe_load(f)

    username = CONFIG['basic_auth']['username']
    password = CONFIG['basic_auth']['password']
    BASIC_AUTH = HTTPBasicAuth(username, password)

def api_call(ip):
    try:
        # Get endpoint configuration
        url = f'https://{ip}/getxml?location=/Configuration'
        print(f"Getting Configuration From {ip}\n")
        response = requests.get(url, headers=HEADERS, verify=False, auth=BASIC_AUTH, timeout=3)
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        with open(f'{CONFIG["host_vars_path"]}{ip}-config.xml', 'wb') as x:
            x.write(response.content)

        # Get endpoint status info
        url = f'https://{ip}/getxml?location=/Status'
        response = requests.get(url, headers=HEADERS, verify=False, auth=BASIC_AUTH, timeout=3)
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        with open(f'{CONFIG["host_vars_path"]}{ip}-status.xml', 'wb') as x:
            x.write(response.content)

        # Get user list
        url = f'https://{ip}/putxml'
        xml = '<Command><UserManagement><User><List></List></User></UserManagement></Command>'
        response = requests.post(url, headers=HEADERS, verify=False, auth=BASIC_AUTH, timeout=3, data=xml)
        response.raise_for_status()  # Raise an exception for non-2xx status codes
        with open(f'{CONFIG["host_vars_path"]}{ip}-command.xml', 'wb') as x:
            x.write(response.content)

        parse_xml(ip)

    except requests.HTTPError as e:
        print(f'HTTP Error occurred while fetching data from endpoint {ip}: {str(e)}')
        with open(f'{CONFIG["output_path"]}BBP_failed.txt', 'a') as f:
            f.write(f'{ip}\n')

    except requests.RequestException as e:
        print(f'Error occurred while making API request to endpoint {ip}: {str(e)}')
        with open(f'{CONFIG["output_path"]}BBP_failed.txt', 'a') as f:
            f.write(f'{ip}\n')

    except Exception as e:
        print(f'An error occurred while processing endpoint {ip}: {str(e)}')
        with open(f'{CONFIG["output_path"]}BBP_failed.txt', 'a') as f:
            f.write(f'{ip}\n')


def parse_xml(ip):
    try:
        config_tree = ET.parse(f'{CONFIG["host_vars_path"]}{ip}-config.xml')
        status_tree = ET.parse(f'{CONFIG["host_vars_path"]}{ip}-status.xml')
        command_tree = ET.parse(f'{CONFIG["host_vars_path"]}{ip}-command.xml')

        parse_config_xml(config_tree)
        parse_status_xml(status_tree)
        parse_command_xml(command_tree)

        print('XML data parsed')

    except Exception as e:
        print(f'Failed to parse XML for endpoint {ip}: {str(e)}')

    finally:
        remove_files(ip)


def parse_config_xml(tree):
    root = tree.getroot()
    print(root)
    system_info['System_Name'] = root.find('./SystemUnit/Name').text
    system_info['H323ID'] = root.find('./H323/H323Alias/ID').text
    system_info['Gate_Keeper'] = root.find('./H323/Gatekeeper/Address').text
    system_info['E_164'] = root.find('./H323/H323Alias/E164').text
    system_info['System_MTU'] = root.find('./Network/MTU').text
    system_info['SNMP_Status'] = root.find('./NetworkServices/SNMP/Mode').text
    print('Parsing Complete')


def parse_status_xml(tree):
    root = tree.getroot()
    system_info['MAC_Address'] = root.find('./Network/Ethernet/MacAddress').text
    system_info['Hardware_Serial'] = root.find('./SystemUnit/Hardware/Module/SerialNumber').text
    system_info['IP_address'] = root.find('./Network/IPv4/Address').text
    system_info['Ethernet_Link'] = root.find('./Network/Ethernet/Speed').text
    system_info['Router_IP'] = root.find('.//Network/IPv4/Gateway').text
    system_info['Model'] = root.find('./SystemUnit/ProductId').text
    system_info['Latest_Software'] = 'ce 9.15.3'
    system_info['sw_version'] = root.find('./SystemUnit/Software/Version').text
    system_info['switch_hostname'] = root.find('./Network/CDP/DeviceId').text
    system_info['switchport'] = root.find('./Network/CDP/PortID').text
    system_info['Provisioned'] = root.find('./Provisioning/Status').text
    system_info['Registrar'] = root.find('./SIP/Proxy/Address').text
    system_info['Registered'] = root.find('./SIP/Registration/Status').text
    system_info['SIP_URI'] = root.find('./SIP/Registration/URI').text

def parse_command_xml(tree):
    root = tree.getroot()
    system_info['Users'] = len(root.find('./UserListResult'))


def remove_files(ip):
    os.remove(f'{CONFIG["host_vars_path"]}{ip}-config.xml')
    os.remove(f'{CONFIG["host_vars_path"]}{ip}-status.xml')
    os.remove(f'{CONFIG["host_vars_path"]}{ip}-command.xml')


def apply_mtu(ip):
    if re.search(r"^1280", (system_info['System_MTU'])):
        print('MTU check passed')
    else:
        print('Changing MTU to 1280')
        url = f'https://{ip}/putxml'
        xml = '<Configuration><Network><MTU>1280</MTU></Network></Configuration>'
        response = requests.post(url, headers=HEADERS, verify=False, auth=BASIC_AUTH, timeout=5, data=xml)
        url = f'https://{ip}/getxml?location=/Configuration'
        response = requests.get(url, headers=HEADERS, verify=False, auth=BASIC_AUTH, timeout=5)
        with open(f'{CONFIG["host_vars_path"]}{ip}-config.xml', 'wb') as x:
            x.write(response.content)

        tree = ET.parse(f'{CONFIG["host_vars_path"]}{ip}-config.xml')
        root = tree.getroot()

        system_info['System_MTU'] = root.find('./Network/MTU').text
        os.remove(f'{CONFIG["host_vars_path"]}{ip}-config.xml')

        with open(f'{CONFIG["output_path"]}change-log.txt', 'a') as x:
            x.write(f'{ip}' + ' MTU changed to 1280')

def apply_snmp(ip):
    if re.search(r"^Off", (system_info['SNMP_Status'])):
        print('SNMP check passed')
    else:
        print('Disabling SNMP')
        url = f'https://{ip}/putxml'
        xml = '<Configuration><NetworkServices><SNMP><Mode>Off</Mode></SNMP></NetworkServices></Configuration>'
        response = requests.post(url, headers=HEADERS, verify=False, auth=BASIC_AUTH, timeout=5, data=xml)
        url = f'https://{ip}/getxml?location=/Configuration'
        response = requests.get(url, headers=HEADERS, verify=False, auth=BASIC_AUTH, timeout=5)
        with open(f'{CONFIG["host_vars_path"]}{ip}-config.xml', 'wb') as x:
            x.write(response.content)

        tree = ET.parse(f'{CONFIG["host_vars_path"]}{ip}-config.xml')
        root = tree.getroot()

        system_info['SNMP_Status'] = root.find('./NetworkServices/SNMP/Mode').text
        os.remove(f'{CONFIG["host_vars_path"]}{ip}-config.xml')

        with open(f'{CONFIG["output_path"]}change-log.txt', 'a') as x:
            x.write(f'{ip}' + ' SNMP Disabled')

def write_csv():
    if os.path.exists(f'{CONFIG["output_path"]}BBP.csv'):
        with open(f'{CONFIG["output_path"]}BBP.csv', 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, system_info.keys())
            writer.writerow(system_info)
            print('CSV Updated...\n')
    else:
        with open(f'{CONFIG["output_path"]}BBP.csv', 'a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, system_info.keys())
            writer.writeheader()
            writer.writerow(system_info)
            print('CSV Updated...')

def main():
    load_config()

    # Get list of endpoints
    list_file = f'{CONFIG["path"]}list.txt'
    if not os.path.exists(list_file):
        print("Endpoint list file does not exist. Please populate the list.")
    else:
        with open(list_file) as f:
            endpoints = [line.rstrip() for line in f]

    # Remove old output files
    if os.path.exists(f'{CONFIG["output_path"]}BBP.csv'):
        os.remove(f'{CONFIG["output_path"]}BBP.csv')
    if os.path.exists(f'{CONFIG["output_path"]}BBP_failed.txt'):
        os.remove(f'{CONFIG["output_path"]}BBP_failed.txt')
    if os.path.exists(f'{CONFIG["output_path"]}change-log.txt'):
        os.remove(f'{CONFIG["output_path"]}change-log.txt')

    for item in endpoints:
        try:
            api_call(item)
            apply_mtu(item)
            apply_snmp(item)
            write_csv()
            print(item + ' complete\n\n')

        except:
            print('Failed....Skipping Device \n')


if __name__ == '__main__':
    main()