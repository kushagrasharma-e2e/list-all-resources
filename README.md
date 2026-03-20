# E2E Services Inventory Dashboard

A Streamlit-based dashboard to visualise and audit service usage across E2E Networks projects and locations.

This tool helps identify which services are active in which projects and regions using E2E APIs.

---

## Features

* Secure input for API credentials (no `.env` required)
* Multi-location support (Delhi, Mumbai, Chennai)
* Coverage of multiple E2E services:

  * Compute (Nodes)
  * Kubernetes
  * Load Balancers
  * Object Storage
  * DBaaS
  * CDN
  * VPC, Security Groups, and more
* Tabular visualization of service usage
* Export results as CSV
* Error tracking for failed API calls

---

## Tech Stack

* Python 3.x
* Streamlit
* Requests
* Pandas

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-repo/e2e-services-inventory.git
cd e2e-services-inventory
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

If you do not have a `requirements.txt`, install manually:

```bash
pip install streamlit requests pandas
```

---

## Running the App

```bash
streamlit run app.py
```

---

## Usage

1. Open the app in your browser (typically [http://localhost:8501](http://localhost:8501))
2. Enter credentials in the sidebar:

   * E2E API Key
   * E2E Auth Token
3. Select one or more locations
4. Click "Fetch Services"

---

## Output

The app displays:

* Service Name
* Location
* Project Name

You can:

* View results in a table
* Download results as a CSV file

---

## How It Works

1. Fetches Owner CRN via:

   ```
   iam/multi-crn/
   ```

2. Retrieves project list:

   ```
   pbac/projects-header/
   ```

3. Iterates over:

   * Projects
   * Locations
   * Service endpoints

4. Checks if resources exist (`data > 0`) and logs results

---

## Error Handling

* API failures are captured and displayed in an Errors section
* Invalid JSON responses are safely handled
* Execution continues even if some endpoints fail

---

## Security Notes

* Credentials are entered via UI and not stored
* Avoid sharing API keys or tokens publicly
* Use scoped or limited credentials where possible

---

## Supported Services

Includes (but not limited to):

* Nodes
* Load Balancers
* Auto Scaling
* Kubernetes
* Volumes
* Images
* Backups
* Functions (FaaS)
* Object Storage
* Container Registry
* DBaaS
* CDN
* Firewall
* DNS
* VPC
* Security Groups
* Secrets Management
* Disaster Recovery

---

## Future Improvements

* Service usage summary (counts per project)
* Charts and visual analytics
* Filtering by service type
* Historical usage tracking
* Multi-user support

---

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

---

## License

Apache License 2.0

