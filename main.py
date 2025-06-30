from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import jwt
import logging
import dotenv
from datetime import datetime

from azure.identity import ClientSecretCredential

from msfabricpysdkcore import FabricClientCore
from sqlconnection import SQLConnection  # Assuming you have a SQLConnection class defined

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
# Only mount static files if the directory exists
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

dotenv.load_dotenv(".env", override=True)
tenant_id = os.getenv("TENANT_ID")
client_id = os.getenv("CLIENT_ID")
client_object_id = os.getenv("CLIENT_OBJECT_ID")
client_secret = os.getenv("CLIENT_SECRET")
db_server = os.getenv("DB_SERVER")
db_name = os.getenv("DB_NAME")
credential = ClientSecretCredential(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)

sql_connection = SQLConnection(
    server=db_server, database=db_name,
    credential=credential
)
fcc = FabricClientCore(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)

def get_fresh_workspaces():
    """Helper function to fetch fresh workspace data from the database"""
    try:
        workspaces_df = sql_connection.fetch_workspaces()
        workspaces_list = workspaces_df.to_dict(orient="records")
        logger.info(f"Fetched fresh workspaces: {len(workspaces_list)} records")
        return workspaces_list
    except Exception as e:
        logger.error(f"Error fetching workspaces from database: {e}")
        return []

def get_form_options_data():
    """Helper function to fetch form options data from the database"""
    try:
        # Fetch domains
        domains = sql_connection.get_domains()
        domains = list(domains["domainName"])
        logger.info(f"Fetched domains: {domains}")
        dom_list = [{"value": dom, "label": dom} for dom in domains]

        # Fetch capacities from the database
        capacities = sql_connection.get_capacities()
        capacity_names = [capacity["capacityName"] for _, capacity in capacities.iterrows()]
        capacity_list = [{"value": name, "label": name} for name in capacity_names]
        regions = capacities["region"].unique().tolist()
        region_list = [{"value": region, "label": region} for region in regions]
        logger.info(f"Fetched capacities: {capacities}")

        return {
            "capacities": capacity_list,
            "domains": dom_list,
            "regions": region_list,
            "workspace_types": [
                {"value": "Single", "label": "Single"},
                {"value": "DevQaProd", "label": "DevQaProd"},
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching form options from database: {e}")
        return {
            "capacities": [],
            "domains": [],
            "regions": [],
            "workspace_types": [
                {"value": "Single", "label": "Single"},
                {"value": "DevQaProd", "label": "DevQaProd"},
            ]
        }

# Initialize data on startup
workspaces = get_fresh_workspaces()
form_options = get_form_options_data()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, view: str = "admin", success: str = None, error: str = None, workspace: str = None, user: str = None, role: str = None, item: str = None, type: str = None, workload: str = None):
    # Get user information from Easy Auth headers
    current_user = get_user_or_fallback(request)
    
    # Get fresh data from database
    fresh_workspaces = get_fresh_workspaces()
    fresh_form_options = get_form_options_data()
    
    # Validate view parameter
    if view not in ["admin", "request"]:
        view = "admin"
    
    # Prepare messages
    message = None
    message_type = None
    
    if success == "approved" and workspace:
        message = f"✅ Workspace '{workspace}' has been successfully approved and created in Microsoft Fabric!"
        message_type = "success"
    elif success == "denied" and workspace:
        message = f"❌ Workspace '{workspace}' has been denied."
        message_type = "warning"
    elif success == "user_assigned" and workspace and user and role:
        message = f"✅ User '{user}' has been assigned to workspace '{workspace}' with role '{role}'."
        message_type = "success"
    elif success == "request_submitted":
        message = f"✅ Workspace request has been submitted successfully!"
        message_type = "success"
    elif success == "item_created" and item and type and workspace:
        message = f"✅ {type} '{item}' has been created successfully in workspace '{workspace}'!"
        message_type = "success"
    elif success == "approval_required" and item and type and workspace:
        message = f"📋 {type} '{item}' has been requested in workspace '{workspace}'. Approval required - admin notification sent."
        message_type = "info"
    elif error == "not_found" and workspace:
        message = f"❌ Workspace '{workspace}' was not found in the pending requests."
        message_type = "error"
    elif error == "workspace_not_found" and workspace:
        message = f"❌ Created workspace '{workspace}' was not found."
        message_type = "error"
    elif error == "invalid_email" and user:
        message = f"❌ Invalid email format: '{user}'. Please provide a valid email address."
        message_type = "error"
    elif error == "invalid_role" and role:
        message = f"❌ Invalid role: '{role}'. Please select a valid role."
        message_type = "error"
    elif error == "assignment_failed" and workspace and user:
        message = f"❌ Failed to assign user '{user}' to workspace '{workspace}'. Please try again."
        message_type = "error"
    elif error == "not_eligible" and workload:
        message = f"❌ You are not eligible to create '{workload}' items. Contact admin for access."
        message_type = "error"
    elif error == "creation_failed" and item and type:
        message = f"❌ Failed to create {type} '{item}'. Please try again or contact support."
        message_type = "error"
    elif error == "approval_failed" and workspace:
        message = f"❌ Failed to approve workspace '{workspace}'. Please try again or contact support."
        message_type = "error"
    elif error == "denial_failed" and workspace:
        message = f"❌ Failed to deny workspace '{workspace}'. Please try again or contact support."
        message_type = "error"
    elif error == "request_failed":
        message = f"❌ Failed to submit workspace request. Please try again."
        message_type = "error"
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": current_user,
        "workspaces": fresh_workspaces,
        "form_options": fresh_form_options,
        "current_view": view,
        "message": message,
        "message_type": message_type
    })

@app.post("/toggle-view")
async def toggle_view(request: Request, view: str = Form(...)):
    """Handle view toggle between admin and request"""
    return RedirectResponse(f"/?view={view}", status_code=303)

@app.post("/approve")
async def approve_workspace(workspace_name: str = Form(...)):
    """Approve workspace and create it in Microsoft Fabric"""
    try:
        # Get fresh workspace data from database
        fresh_workspaces = get_fresh_workspaces()
        ws_hits = [ws for ws in fresh_workspaces if ws["WorkspaceName"] == workspace_name]
        
        if not ws_hits:
            logger.warning(f"Workspace {workspace_name} not found in database")
            return RedirectResponse(f"/?view=admin&error=not_found&workspace={workspace_name}", status_code=303)
        
        ws = ws_hits[0]
        ws["Status"] = "created"

        capa = fcc.get_capacity(capacity_name=ws["Capacity"])
        ws_item = fcc.create_workspace(display_name=workspace_name, capacity_id=capa.id)

        # Add role assignment for the requester
        fcc.add_workspace_role_assignment(
            workspace_id=ws_item.id,
            principal={
                "id": ws["RequesterID"],
                "type": "User"
            },
            role='Contributor'
        )
        
        # Update database with new status and workspace ID
        sql_connection.update_workspace(
            workspace=workspace_name, 
            status="created", 
            workspace_id=ws_item.id
        )
        
        logger.info(f"Workspace {workspace_name} has been approved and created with ID: {ws_item.id}")
        
        return RedirectResponse(f"/?view=admin&success=approved&workspace={workspace_name}", status_code=303)
        
    except Exception as e:
        logger.error(f"Error approving workspace {workspace_name}: {e}")
        return RedirectResponse(f"/?view=admin&error=approval_failed&workspace={workspace_name}", status_code=303)

@app.post("/request")
async def request_workspace(
    request: Request,
    capacity: str = Form(...),
    domain: str = Form(...),
    region: str = Form(...),
    name: str = Form(...),
    type_: str = Form(...)
):
    """Submit a new workspace request"""
    try:
        # Get current user information
        current_user = get_user_or_fallback(request)
        
        # Save request to database
        sql_connection.request_workspace(
            workspace=name,
            domain=domain,
            capacity=capacity,
            region=region,
            single_workspace=type_,
            requester=current_user["email"],
            requester_id=current_user["id"],
            request_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        logger.info(f"Workspace request submitted: {name} by {current_user['email']}")
        
        return RedirectResponse("/?success=request_submitted", status_code=303)
        
    except Exception as e:
        logger.error(f"Error submitting workspace request: {e}")
        return RedirectResponse("/?error=request_failed", status_code=303)

@app.post("/deny")
async def deny_workspace(workspace_name: str = Form(...)):
    """Deny a workspace request"""
    try:
        # Get fresh workspace data from database
        fresh_workspaces = get_fresh_workspaces()
        ws_hits = [ws for ws in fresh_workspaces if ws["WorkspaceName"] == workspace_name]
        
        if not ws_hits:
            logger.warning(f"Workspace {workspace_name} not found in database")
            return RedirectResponse(f"/?view=admin&error=not_found&workspace={workspace_name}", status_code=303)
        
        ws = ws_hits[0]
        
        ws["Status"] = "denied"
        # Update database with denied status and reason
        sql_connection.update_workspace(
            workspace=workspace_name, 
            status="denied",
            workspace_id=None,
        )
        
        logger.info(f"Workspace {workspace_name} has been denied.")
        
        return RedirectResponse(f"/?view=admin&success=denied&workspace={workspace_name}", status_code=303)
        
    except Exception as e:
        logger.error(f"Error denying workspace {workspace_name}: {e}")
        return RedirectResponse(f"/?view=admin&error=denial_failed&workspace={workspace_name}", status_code=303)

@app.post("/assign-user")
async def assign_user_to_workspace(
    workspace_name: str = Form(...),
    user_email: str = Form(...),
    role: str = Form(...)
):
    """Assign a user with specific role to a workspace"""
    try:
        # Get fresh workspace data from database
        fresh_workspaces = get_fresh_workspaces()
        ws_hits = [ws for ws in fresh_workspaces if ws["WorkspaceName"] == workspace_name and ws["Status"] == "created"]
        
        if not ws_hits:
            logger.warning(f"Created workspace {workspace_name} not found in database")
            return RedirectResponse(f"/?view=admin&error=workspace_not_found&workspace={workspace_name}", status_code=303)
        
        ws = ws_hits[0]
        workspace_id = ws["WorkspaceId"]
        
        # Validate user email format
        if "@" not in user_email or "." not in user_email:
            logger.warning(f"Invalid email format: {user_email}")
            return RedirectResponse(f"/?view=admin&error=invalid_email&user={user_email}", status_code=303)
        
        # Define role-based privileges following the Streamlit logic
        privileges = []
        if role == "Data Engineer":
            privileges = ["lakehouse", "datapipeline", "notebook"]
        elif role == "Data Scientist":
            privileges = ["notebook", "mlmodel"]
        elif role == "Data Analyst":
            privileges = ["notebook"]  # Basic access for analysts
        elif role == "Data Engineer RTI":
            privileges = ["lakehouse", "datapipeline", "notebook", "dataflow"]  # Extended privileges
        
        if not privileges:
            logger.warning(f"No privileges defined for role: {role}")
            return RedirectResponse(f"/?view=admin&error=invalid_role&role={role}", status_code=303)
        
        # Add scope for user in database
        sql_connection.add_scope_for_user(user_email, workspace_id, privileges)
        
        logger.info(f"User {user_email} assigned to workspace {workspace_name} with role {role} and privileges: {privileges}")
        
        return RedirectResponse(f"/?view=admin&success=user_assigned&workspace={workspace_name}&user={user_email}&role={role}", status_code=303)
        
    except Exception as e:
        logger.error(f"Error assigning user {user_email} to workspace {workspace_name}: {e}")
        return RedirectResponse(f"/?view=admin&error=assignment_failed&workspace={workspace_name}&user={user_email}", status_code=303)

@app.post("/request-workload-item")
async def request_workload_item(
    request: Request,
    workspace_name: str = Form(...),
    workload_type: str = Form(...),
    item_name: str = Form(...)
):
    """Request a workload item in a workspace based on user eligibility"""
    try:
        # Get current user information
        current_user = get_user_or_fallback(request)
        user_email = current_user["email"]
        
        # Get user's created workspaces
        user_workspaces = sql_connection.fetch_workspaces(
            filter=f"WHERE Requester = '{user_email}' AND Status = 'created'"
        )
        
        # Find the selected workspace
        workspace_df = user_workspaces[user_workspaces["WorkspaceName"] == workspace_name]
        
        if workspace_df.empty:
            logger.warning(f"Workspace {workspace_name} not found for user {user_email}")
            return RedirectResponse(f"/?view=request&error=workspace_not_found&workspace={workspace_name}", status_code=303)
        
        workspace_id = workspace_df["WorkspaceId"].iloc[0]
        
        # Get user's eligibility for this workspace
        eligibility_df = sql_connection.fetch_eligibility(user_email, workspace_id)
        
        # Check eligibility for the requested workload type
        eligible_item = eligibility_df[eligibility_df["ItemType"] == workload_type]
        
        if eligible_item.empty:
            logger.warning(f"User {user_email} not eligible for {workload_type} in workspace {workspace_name}")
            return RedirectResponse(f"/?view=request&error=not_eligible&workload={workload_type}", status_code=303)
        
        eligibility_status = eligible_item["Eligibility"].iloc[0]
        
        if eligibility_status == "eligible":
            # User is eligible - create the item directly
            try:
                ws = fcc.get_workspace(name=workspace_name)
                item = ws.create_item(display_name=item_name, type=workload_type)
                
                logger.info(f"Created {workload_type} '{item_name}' in workspace {workspace_name} for user {user_email}")
                return RedirectResponse(f"/?view=request&success=item_created&item={item_name}&type={workload_type}&workspace={workspace_name}", status_code=303)
                
            except Exception as e:
                logger.error(f"Error creating {workload_type} '{item_name}': {e}")
                return RedirectResponse(f"/?view=request&error=creation_failed&item={item_name}&type={workload_type}", status_code=303)
        
        else:
            # User needs approval - this would require implementing an approval workflow
            # For now, we'll just log the request and show a message
            logger.info(f"Approval required for {workload_type} '{item_name}' requested by {user_email} in workspace {workspace_name}")
            return RedirectResponse(f"/?view=request&success=approval_required&item={item_name}&type={workload_type}&workspace={workspace_name}", status_code=303)
        
    except Exception as e:
        logger.error(f"Error processing workload item request: {e}")
        return RedirectResponse(f"/?view=request&error=request_failed", status_code=303)

@app.get("/api/form-options")
async def get_form_options():
    """API endpoint to get fresh form options data"""
    return get_form_options_data()

@app.get("/api/workspace/{workspace_name}")
async def get_workspace_details(workspace_name: str):
    """Get details for a specific workspace"""
    try:
        fresh_workspaces = get_fresh_workspaces()
        workspace = next((ws for ws in fresh_workspaces if ws["WorkspaceName"] == workspace_name), None)
        
        if not workspace:
            return {"error": "Workspace not found"}
        
        return {"workspace": workspace}
        
    except Exception as e:
        logger.error(f"Error fetching workspace details for {workspace_name}: {e}")
        return {"error": "Failed to fetch workspace details"}

@app.get("/api/created-workspaces")
async def get_created_workspaces():
    """API endpoint to get workspaces with 'created' status for user assignment"""
    try:
        fresh_workspaces = get_fresh_workspaces()
        created_workspaces = [ws for ws in fresh_workspaces if ws["Status"] == "created"]
        return {"workspaces": created_workspaces}
    except Exception as e:
        logger.error(f"Error fetching created workspaces: {e}")
        return {"error": "Failed to fetch created workspaces"}

@app.get("/api/user-workspaces/{user_email}")
async def get_user_workspaces(user_email: str):
    """Get workspaces created by a specific user"""
    try:
        user_workspaces = sql_connection.fetch_workspaces(
            filter=f"WHERE Requester = '{user_email}' AND Status = 'created'"
        )
        workspaces_list = user_workspaces.to_dict(orient="records")
        return {"workspaces": workspaces_list}
    except Exception as e:
        logger.error(f"Error fetching user workspaces: {e}")
        return {"error": "Failed to fetch user workspaces"}

@app.get("/api/workspace/{workspace_name}/eligibility/{user_email}")
async def get_workspace_eligibility(workspace_name: str, user_email: str):
    """Get user eligibility for a specific workspace"""
    try:
        # Get workspace details
        user_workspaces = sql_connection.fetch_workspaces(
            filter=f"WHERE Requester = '{user_email}' AND Status = 'created' AND WorkspaceName = '{workspace_name}'"
        )
        
        if user_workspaces.empty:
            return {"error": "Workspace not found or not accessible"}
        
        workspace_id = user_workspaces["WorkspaceId"].iloc[0]
        
        # Get eligibility
        eligibility_df = sql_connection.fetch_eligibility(user_email, workspace_id)
        eligibility_list = eligibility_df.to_dict(orient="records")
        
        return {
            "workspace": workspace_name,
            "workspace_id": workspace_id,
            "eligibility": eligibility_list
        }
        
    except Exception as e:
        logger.error(f"Error fetching workspace eligibility: {e}")
        return {"error": "Failed to fetch workspace eligibility"}

@app.get("/debug/headers")
async def debug_headers(request: Request):
    """
    Debug endpoint to see all headers (useful for Easy Auth troubleshooting)
    """
    headers_dict = dict(request.headers)
    
    # Specifically look for Easy Auth headers
    easyauth_headers = {
        key: value for key, value in headers_dict.items() 
        if key.lower().startswith('x-ms-')
    }
    
    user_info = get_user_from_easyauth(request)
    
    return {
        "all_headers": headers_dict,
        "easyauth_headers": easyauth_headers,
        "extracted_user": user_info
    }

@app.get("/debug/user")
async def debug_user(request: Request):
    """
    Debug endpoint to see current user information
    """
    user_info = get_user_or_fallback(request)
    return {"user": user_info}

def get_user_from_easyauth(request: Request):
    """
    Extract user information from Easy Auth headers
    Similar to Streamlit's st.context.headers
    """
    try:
        # Get user name from Easy Auth header
        user_name = request.headers.get("X-Ms-Client-Principal-Name")
        
        # Get the AAD access token
        token = request.headers.get("X-Ms-Token-Aad-Access-Token")
        
        if not token:
            logger.warning("No AAD access token found in headers")
            return None
            
        # Decode JWT token without signature verification (similar to your Streamlit code)
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Extract user information
        user_mail = decoded.get("upn")  # User Principal Name
        user_id = decoded.get("oid")    # Object ID
        
        logger.info(f"User authenticated: {user_name} ({user_mail})")
        
        return {
            "name": user_name,
            "email": user_mail,
            "id": user_id,
            "decoded_token": decoded  # Include full decoded token for debugging
        }
        
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error extracting user from Easy Auth: {e}")
        return None

def get_user_or_fallback(request: Request):
    """
    Get user from Easy Auth or return fallback user for development
    """
    # Try to get user from Easy Auth headers
    auth_user = get_user_from_easyauth(request)
    
    if auth_user:
        return auth_user
    
    # Fallback to mock user for development (when Easy Auth is not available)
    logger.info("Using fallback user (Easy Auth not available)")
    return {
        "name": "Admin User (Fallback)",
        "email": "admin@-----.com",
        "id": "fallback-user-id"
    }