from azure.identity import AzureCliCredential
import os
import pyodbc, struct
import pandas as pd


# CREATE TABLE [dbo].[Workspaces] (
# Id INT IDENTITY(1,1) PRIMARY KEY,
# Status NVARCHAR(50),
# WorkspaceName NVARCHAR(100),
# WorkspaceId NVARCHAR(100),
# Domain NVARCHAR(100),
# Capacity NVARCHAR(100),
# Region NVARCHAR(50),
# WorkspaceType NVARCHAR(50),
# Requester NVARCHAR(100),
# RequesterID NVARCHAR(100),
# RequestDate DATETIME
#  );

# CREATE TABLE [dbo].[Eligibility] (
#     Id INT IDENTITY(1,1) PRIMARY KEY,
#     Eligibility NVARCHAR(50),
#     ItemType NVARCHAR(50),
#     WorkspaceId NVARCHAR(100),
#     UserEmail NVARCHAR(100)
# );


# CREATE TABLE Domains (
#     domainId INT IDENTITY(1,1) PRIMARY KEY,
#     domainName NVARCHAR(255) NOT NULL
# );

# INSERT INTO Domains (domainName)
# VALUES 
#     ('Sales'),
#     ('Finance'),
#     ('Marketing');


# CREATE TABLE Capacities (
#     capacityId INT PRIMARY KEY,
#     capacityName NVARCHAR(105) NOT NULL,
#     region NVARCHAR(30)
# );
# INSERT INTO Capacities (capacityId, capacityName, region)
# VALUES 
#     ('---', 'snowflakeshortcut', 'West US 2'),
#     ('---', 'northeurope20250401', 'North Europe'),
#     ('---', 'sweden20250120', 'Sweden Central')

# CREATE TABLE UserLookup
#  (
#     userMail NVARCHAR(105) NOT NULL,
#     userObjectId NVARCHAR(105) NOT NULL
# );

# INSERT INTO UserLookup (userMail, userObjectId) 
# VALUES ('admin@asdfasdf.com', '---'), 
# ('johndoe@asdfasdf.com', 'e----')

class SQLConnection:

    def __init__(self, server, database, credential):
        self.server = server
        self.database = database
        self.credential = credential


    def run_query(self, query, query_type="SELECT"):

        credential = self.credential
        token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("UTF-16-LE")

        token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
        SQL_COPT_SS_ACCESS_TOKEN = 1256  # This connection option is defined by microsoft in msodbcsql.h

        # Connection parameters
        connection_string = f"Driver={{ODBC Driver 18 for SQL Server}};Server={self.server};Database={self.database};"

        # Connect with Entra ID (Azure AD) token
        conn = pyodbc.connect(connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
        cursor = conn.cursor()

        # Test the connection
        cursor.execute(query)
        if query_type=="SELECT":
            rows = cursor.fetchall()

            column_names = [column[0] for column in cursor.description]
            return_value = pd.DataFrame.from_records(rows, columns=column_names)
        else:
            cursor.execute("COMMIT;")
            return_value = "success"

        # Close the connection
        cursor.close()
        conn.close()
        return return_value

    def fetch_workspaces(self, filter = ""):

        columns = ["Status", "WorkspaceName", "WorkspaceId", "Domain", "Capacity", "Region", "WorkspaceType", "Requester", "RequesterID", "RequestDate"]
        columns_joined = ", ".join(columns)
        sql = f"SELECT {columns_joined} from dbo.Workspaces {filter};"
        return self.run_query(sql)
    
    def request_workspace(self, workspace, domain, capacity, region, single_workspace, requester, requester_id, request_date):

        sql = f"""INSERT INTO [dbo].[Workspaces] (Status, WorkspaceName, WorkspaceId, Domain, Capacity, Region, WorkspaceType, Requester, RequesterID, RequestDate)
        VALUES ('requested', '{workspace}', 'TBD', '{domain}','{capacity}','{region}','{single_workspace}','{requester}', '{requester_id}', '{request_date}');"""

        return self.run_query(sql, "INSERT")

    def update_workspace(self, workspace, status, workspace_id):
        sql = f"UPDATE dbo.Workspaces SET Status = '{status}', WorkspaceId = '{workspace_id}' WHERE WorkspaceName = '{workspace}';"
        return self.run_query(sql, "UPDATE")

    def delete_workspaces(self):

        sql = "DELETE FROM dbo.Workspaces;"
        return self.run_query(sql, "DELETE")

    def fetch_eligibility(self, user_mail, workspace_id):
        columns = ["Eligibility", "ItemType", "WorkspaceId", "UserEmail"]
        columns_joined = ", ".join(columns)
        sql = f"SELECT {columns_joined} from dbo.Eligibility WHERE UserEmail = '{user_mail}' and WorkspaceId = '{workspace_id}';"
        return self.run_query(sql)

    def add_scope_for_user(self, user_mail, ws_id, privileges):

        for priv in privileges:
            sql = f"""INSERT INTO [dbo].[Eligibility] (UserEmail, WorkspaceId, ItemType, Eligibility)
            VALUES ('{user_mail}', '{ws_id}', '{priv}', 'eligible');"""

            self.run_query(sql, "INSERT")

    def get_domains(self):
        sql = "SELECT [domainName]  FROM [dbo].[Domains];"
        return self.run_query(sql)
    
    def get_capacities(self):
        sql = "SELECT [capacityId], [capacityName], [region] FROM [dbo].[Capacities];"
        return self.run_query(sql)