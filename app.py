import requests
import pandas as pd
import streamlit as st

BASE_URL = "https://api.e2enetworks.com/myaccount/api/v1/"

ENDPOINTS = {
    "nodes/": "Nodes",
    "appliances/": "Load Balancers",
    "scaler/scalegroups?page_no=1&per_page=50": "Auto Scaling",
    "kubernetes/": "Kubernetes",
    "block_storage/": "Volumes",
    "images/saved-images/": "Images",
    "cdpbackup/": "CDP Backups",
    "faas/namespace/": "Functions",
    "efs/": "Scalable File System",
    "storage/buckets/": "Object Storage",
    "container_registry/projects-details/": "Container Registry",
    "epfs/": "EPFS",
    "rds/cluster/": "DBaaS",
    "rds/parameter-group/": "Parameter Group",
    "cdn/distributions/": "CDN",
    "fortigate/list": "Firewall",
    "e2e_dns/forward/": "DNS",
    "reserve_ips/": "Reserve IP",
    "vpc/list/": "VPC",
    "security_group/": "Security Group",
    "vault/": "E2E Secrets Managment",
    "draas/": "Disaster Recovery",
}


def safe_json(response):
    try:
        return response.json()
    except Exception:
        return {}


def get_owner_crn(session, api_key, auth_token):
    url = BASE_URL + "iam/multi-crn/"
    response = session.get(
        url,
        params={"apikey": api_key},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30,
    )
    response.raise_for_status()

    payload = safe_json(response)
    data = payload.get("data", {}).get("crn_data", []) or []

    owner_crn = next(
        (item.get("crn") for item in data if item.get("iam_type") == "Owner"),
        None,
    )
    return owner_crn


def get_projects(session, api_key, auth_token, owner_crn):
    url = BASE_URL + "pbac/projects-header/"
    response = session.get(
        url,
        params={"apikey": api_key, "crn": owner_crn},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30,
    )
    response.raise_for_status()

    payload = safe_json(response)
    project_list = payload.get("data", []) or []

    project_ids = {}
    for project in project_list:
        project_id = project.get("project_id")
        project_name = project.get("name")
        if project_id and project_name:
            project_ids[project_id] = project_name

    return project_ids


def fetch_service_usage(session, api_key, auth_token, project_ids, locations):
    rows = []
    errors = []

    for project_id, project_name in project_ids.items():
        for location in locations:
            for endpoint, service_name in ENDPOINTS.items():
                try:
                    response = session.get(
                        f"{BASE_URL}{endpoint}",
                        headers={"Authorization": f"Bearer {auth_token}"},
                        params={
                            "apikey": api_key,
                            "location": location,
                            "project_id": project_id,
                        },
                        timeout=30,
                    )

                    payload = safe_json(response)
                    data = payload.get("data", [])

                    if not isinstance(data, list):
                        continue

                    if len(data) > 0:
                        if service_name == "Security Group" and len(data) < 2:
                            continue

                        rows.append(
                            {
                                "Service": service_name,
                                "Location": location,
                                "Project Name": project_name,
                            }
                        )

                except Exception as e:
                    errors.append(
                        {
                            "endpoint": endpoint,
                            "location": location,
                            "project_id": project_id,
                            "error": str(e),
                        }
                    )

    return rows, errors


st.set_page_config(page_title="E2E Services Inventory", layout="wide")
st.title("E2E Services Inventory")
st.caption("Check which services are being used across projects and locations.")

with st.sidebar:
    st.header("Credentials")
    api_key = st.text_input("E2E API Key", type="password")
    auth_token = st.text_input("E2E Auth Token", type="password")

    st.header("Filters")
    locations = st.multiselect(
        "Locations",
        options=["Delhi", "Mumbai", "Chennai"],
        default=["Delhi", "Mumbai", "Chennai"],
    )

    run_btn = st.button("Fetch Services", use_container_width=True)

if run_btn:
    if not api_key or not auth_token:
        st.error("Please enter both E2E API Key and E2E Auth Token.")
    elif not locations:
        st.error("Please select at least one location.")
    else:
        session = requests.Session()

        try:
            with st.spinner("Fetching owner CRN..."):
                owner_crn = get_owner_crn(session, api_key, auth_token)

            if not owner_crn:
                st.error("Owner CRN not found.")
                st.stop()

            with st.spinner("Fetching project list..."):
                project_ids = get_projects(session, api_key, auth_token, owner_crn)

            if not project_ids:
                st.warning("No projects found.")
                st.stop()

            with st.spinner("Checking services across projects and locations..."):
                rows, errors = fetch_service_usage(
                    session, api_key, auth_token, project_ids, locations
                )

            if rows:
                df = pd.DataFrame(rows).sort_values(
                    by=["Project Name", "Location", "Service"]
                )
                st.success(f"Found {len(df)} matching service entries.")
                st.dataframe(df, use_container_width=True)

                csv_data = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download CSV",
                    data=csv_data,
                    file_name="e2e_services_inventory.csv",
                    mime="text/csv",
                )
            else:
                st.info("No services found for the selected locations/projects.")

            if errors:
                with st.expander(f"Errors ({len(errors)})"):
                    st.dataframe(pd.DataFrame(errors), use_container_width=True)

        except requests.HTTPError as e:
            st.error(f"HTTP error: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")
