import requests
import pandas as pd
import streamlit as st

BASE_URL = "https://api.e2enetworks.com/myaccount/api/v1/"

ENDPOINTS = [
    ("nodes/", "Nodes"),
    ("appliances/", "Load Balancers"),
    ("scaler/scalegroups?page_no=1&per_page=50", "Auto Scaling"),
    ("kubernetes/", "Kubernetes"),
    ("block_storage/", "Volumes"),
    ("images/saved-images/", "Images"),
    ("cdpbackup/", "CDP Backups"),
    ("faas/namespace/", "Functions"),
    ("efs/", "Scalable File System"),
    ("storage/buckets/", "Object Storage"),
    ("container_registry/projects-details/", "Container Registry"),
    ("epfs/", "EPFS"),
    ("rds/cluster/", "DBaaS"),
    ("rds/parameter-group/", "Parameter Group"),
    ("cdn/distributions/", "CDN"),
    ("fortigate/list", "Firewall"),
    ("e2e_dns/forward/", "DNS"),
    ("reserve_ips/", "Reserve IP"),
    ("vpc/list/", "VPC"),
    ("security_group/", "Security Group"),
    ("vault/", "E2E Secrets Management"),
    ("draas/", "Disaster Recovery"),
]

DEFAULT_LOCATIONS = ["Delhi", "Mumbai", "Chennai"]


def safe_json(response):
    try:
        return response.json()
    except Exception:
        return {}


def get_session():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


def get_owner_crn(session, api_key, auth_token):
    response = session.get(
        BASE_URL + "iam/multi-crn/",
        params={"apikey": api_key},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30,
    )
    response.raise_for_status()

    payload = safe_json(response)
    crn_data = payload.get("data", {}).get("crn_data", []) or []
    return next(
        (item.get("crn") for item in crn_data if item.get("iam_type") == "Owner"),
        None,
    )


def get_projects(session, api_key, auth_token, owner_crn):
    response = session.get(
        BASE_URL + "pbac/projects-header/",
        params={"apikey": api_key, "crn": owner_crn},
        headers={"Authorization": f"Bearer {auth_token}"},
        timeout=30,
    )
    response.raise_for_status()

    payload = safe_json(response)
    items = payload.get("data", []) or []

    return [
        {"project_id": item.get("project_id"), "project_name": item.get("name")}
        for item in items
        if item.get("project_id") and item.get("name")
    ]


def check_endpoint(session, api_key, auth_token, endpoint, location, project_id):
    response = session.get(
        BASE_URL + endpoint,
        headers={"Authorization": f"Bearer {auth_token}"},
        params={
            "apikey": api_key,
            "location": location,
            "project_id": project_id,
        },
        timeout=30,
    )
    response.raise_for_status()

    payload = safe_json(response)
    data = payload.get("data", [])
    return data if isinstance(data, list) else []


def has_meaningful_data(service_name, data):
    if service_name == "Security Group":
        return len(data) >= 2
    return len(data) > 0


def init_state():
    defaults = {
        "scan_running": False,
        "stop_scan": False,
        "rows": [],
        "errors": [],
        "projects": [],
        "checks": 0,
        "matches": 0,
        "projects_scanned": 0,
        "total_steps": 1,
        "scan_complete": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_scan_state():
    st.session_state.rows = []
    st.session_state.errors = []
    st.session_state.projects = []
    st.session_state.checks = 0
    st.session_state.matches = 0
    st.session_state.projects_scanned = 0
    st.session_state.total_steps = 1
    st.session_state.stop_scan = False
    st.session_state.scan_complete = False


def build_results_df(rows):
    if not rows:
        return pd.DataFrame(columns=["Project Name", "Location", "Service"])
    return (
        pd.DataFrame(rows)
        .drop_duplicates()
        .sort_values(["Project Name", "Location", "Service"])
        .reset_index(drop=True)
    )


def build_project_summary_df(results_df):
    if results_df.empty:
        return pd.DataFrame(columns=["Project Name", "Services Found"])

    return (
        results_df.groupby("Project Name")
        .size()
        .reset_index(name="Services Found")
        .sort_values(["Services Found", "Project Name"], ascending=[False, True])
        .reset_index(drop=True)
    )


def render_live_ui(results_placeholder, summary_placeholder, download_placeholder):
    results_df = build_results_df(st.session_state.rows)
    summary_df = build_project_summary_df(results_df)

    with results_placeholder.container():
        st.subheader("Live Results")

        if results_df.empty:
            st.info("No services found yet.")
        else:
            st.dataframe(results_df, use_container_width=True, hide_index=True)

    with summary_placeholder.container():
        st.subheader("Projects with Matches")

        if summary_df.empty:
            st.caption("No matches yet.")
        else:
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

    with download_placeholder.container():
        if not results_df.empty:
            csv_data = results_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Download CSV",
                data=csv_data,
                file_name="e2e_services_inventory.csv",
                mime="text/csv",
                use_container_width=True,
            )


def main():
    st.set_page_config(page_title="E2E Services Inventory", layout="wide")
    init_state()

    st.title("E2E Services Inventory")
    st.caption("Services appear live as they are discovered across projects and locations.")

    with st.sidebar:
        st.subheader("Credentials")
        api_key = st.text_input("E2E API Key", type="password")
        auth_token = st.text_input("E2E Auth Token", type="password")

        st.subheader("Locations")
        locations = st.multiselect(
            "Select locations",
            DEFAULT_LOCATIONS,
            default=DEFAULT_LOCATIONS,
        )

        col1, col2 = st.columns(2)
        with col1:
            start_clicked = st.button("Start Scan", use_container_width=True)
        with col2:
            stop_clicked = st.button("Stop", use_container_width=True)

    if start_clicked:
        reset_scan_state()
        st.session_state.scan_running = True

    if stop_clicked:
        st.session_state.stop_scan = True

    if not st.session_state.scan_running:
        st.info("Enter credentials, choose locations, and click Start Scan.")
        return

    if not api_key or not auth_token:
        st.error("Please provide both E2E API Key and E2E Auth Token.")
        return

    if not locations:
        st.error("Please select at least one location.")
        return

    status_box = st.empty()
    progress_bar = st.progress(0)

    m1, m2, m3, m4 = st.columns(4)
    projects_metric = m1.empty()
    matches_metric = m2.empty()
    checks_metric = m3.empty()
    errors_metric = m4.empty()

    st.divider()
    left_col, right_col = st.columns([2.2, 1])

    with left_col:
        results_placeholder = st.empty()

    with right_col:
        summary_placeholder = st.empty()
        download_placeholder = st.empty()

    st.divider()
    errors_expander = st.expander("Errors", expanded=False)
    errors_placeholder = errors_expander.empty()

    session = get_session()

    try:
        status_box.info("Fetching account details...")
        owner_crn = get_owner_crn(session, api_key, auth_token)

        if not owner_crn:
            st.error("Owner CRN not found.")
            return

        status_box.info("Fetching projects...")
        projects = get_projects(session, api_key, auth_token, owner_crn)

        if not projects:
            st.warning("No projects found.")
            return

        st.session_state.projects = projects
        st.session_state.total_steps = len(projects) * len(locations) * len(ENDPOINTS)

        render_live_ui(results_placeholder, summary_placeholder, download_placeholder)

        for project_index, project in enumerate(projects, start=1):
            project_id = project["project_id"]
            project_name = project["project_name"]

            for location in locations:
                for endpoint, service_name in ENDPOINTS:
                    if st.session_state.stop_scan:
                        break

                    status_box.info(
                        f"Scanning {project_index}/{len(projects)} • "
                        f"{project_name} • {location} • {service_name}"
                    )

                    try:
                        data = check_endpoint(
                            session=session,
                            api_key=api_key,
                            auth_token=auth_token,
                            endpoint=endpoint,
                            location=location,
                            project_id=project_id,
                        )

                        if has_meaningful_data(service_name, data):
                            st.session_state.rows.append(
                                {
                                    "Project Name": project_name,
                                    "Location": location,
                                    "Service": service_name,
                                }
                            )
                            st.session_state.matches += 1

                            render_live_ui(
                                results_placeholder,
                                summary_placeholder,
                                download_placeholder,
                            )

                    except Exception as e:
                        st.session_state.errors.append(
                            {
                                "Project Name": project_name,
                                "Project ID": project_id,
                                "Location": location,
                                "Service": service_name,
                                "Endpoint": endpoint,
                                "Error": str(e),
                            }
                        )

                    st.session_state.checks += 1

                    progress_bar.progress(
                        min(
                            st.session_state.checks / st.session_state.total_steps,
                            1.0,
                        )
                    )

                    projects_metric.metric("Projects", len(projects))
                    matches_metric.metric("Matches Found", st.session_state.matches)
                    checks_metric.metric("Checks Completed", st.session_state.checks)
                    errors_metric.metric("Errors", len(st.session_state.errors))

                    with errors_placeholder.container():
                        if st.session_state.errors:
                            st.dataframe(
                                pd.DataFrame(st.session_state.errors),
                                use_container_width=True,
                                hide_index=True,
                            )
                        else:
                            st.caption("No errors captured.")

                if st.session_state.stop_scan:
                    break

            st.session_state.projects_scanned = project_index
            if st.session_state.stop_scan:
                break

        st.session_state.scan_complete = True
        st.session_state.scan_running = False

        if st.session_state.stop_scan:
            status_box.warning("Scan stopped. Showing partial results.")
        else:
            status_box.success("Scan complete.")

    except requests.HTTPError as e:
        st.session_state.scan_running = False
        st.error(f"HTTP error: {e}")
    except Exception as e:
        st.session_state.scan_running = False
        st.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
