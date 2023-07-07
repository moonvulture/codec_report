# Codec Compliance Report

The Codec Compliance Report is a script that retrieves configuration and status information from a list of endpoints and generates a CSV report. It uses the Cisco API to communicate with the endpoints and extract the necessary data.

## Features

- Retrieve endpoint configuration and status information
- Generate a CSV report with the collected data
- Apply configuration changes to endpoints (e.g., MTU, SNMP)
- Error handling for failed API requests

## Installation

1. Clone the repository

2. Navigate to the project directory:
    ```bash
    cd codec-compliance-report

3. Install the required dependencies:
    ```bash
    pip install -r requirements.txt


## Usage

1. Prepare the list of endpoints by creating a text file called `list.txt` in the project directory. Each endpoint should be listed on a separate line.

2. Configure the script by editing the `config.yaml` file. Specify the necessary details such as API credentials and file paths.

3. Run the script:
    ```bash
    python report.py


4. The script will retrieve the configuration and status information from each endpoint, apply any necessary changes, and generate a CSV report in the `output` directory.

## Configuration

The `config.yaml` file contains the following configuration options:

- `api_username`: Username for API authentication
- `api_password`: Password for API authentication
- `path`: Path to the project directory
- `host_vars_path`: Path to store the intermediate host variables XML files
- `output_path`: Path to store the generated CSV report and log files

Make sure to populate the `list.txt` file with the list of endpoints to be processed.






